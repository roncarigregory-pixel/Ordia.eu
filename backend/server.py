"""Ordia — AI-powered order automation platform (backend API).

Architecture:
- Multi-tenant: every domain document is scoped by `company_id`.
- Auth: JWT Bearer tokens (email/password), bcrypt hashing.
- Ingestion layer normalizes any input (text / csv / xlsx / pdf / image) into a
  single extraction pipeline powered by Claude Sonnet 4.6 via emergentintegrations.
- Domain: companies, users, products (catalog), orders.
"""
from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import io
import json
import uuid
import base64
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import bcrypt
import jwt
import pandas as pd
from pypdf import PdfReader
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

from catalog_seed import SEED_CATALOG

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ordia")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
TOKEN_TTL_DAYS = 7
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

app = FastAPI(title="Ordia API", version="1.0.0")
api = APIRouter(prefix="/api")

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def create_access_token(user_id: str, company_id: str, email: str) -> str:
    payload = {
        "sub": user_id, "company_id": company_id, "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=TOKEN_TTL_DAYS), "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else None
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class RegisterBody(BaseModel):
    company_name: str
    name: str
    email: EmailStr
    password: str = Field(min_length=6)

class LoginBody(BaseModel):
    email: EmailStr
    password: str

class ProductBody(BaseModel):
    sku: str
    name: str
    category: str = "General"
    unit: str = "unit"
    pack_size: str = ""
    price: float = 0.0
    aliases: List[str] = []

class LineItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    raw_text: str = ""
    quantity: float = 1
    unit: str = "unit"
    matched_product_id: Optional[str] = None
    matched_sku: Optional[str] = None
    matched_name: Optional[str] = None
    price: float = 0.0
    confidence: float = 0.0
    needs_review: bool = True

class OrderUpdate(BaseModel):
    customer_name: Optional[str] = None
    delivery_date: Optional[str] = None
    notes: Optional[str] = None
    line_items: Optional[List[LineItem]] = None
    status: Optional[str] = None

# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
async def seed_company_catalog(company_id: str):
    docs = []
    for p in SEED_CATALOG:
        docs.append({
            "id": str(uuid.uuid4()), "company_id": company_id, **p,
            "created_at": now_iso(),
        })
    if docs:
        await db.products.insert_many(docs)

@api.post("/auth/register")
async def register(body: RegisterBody):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    await db.companies.insert_one({
        "id": company_id, "name": body.company_name, "created_at": now_iso(),
    })
    await db.users.insert_one({
        "id": user_id, "company_id": company_id, "email": email, "name": body.name,
        "password_hash": hash_password(body.password), "role": "admin", "created_at": now_iso(),
    })
    await seed_company_catalog(company_id)
    token = create_access_token(user_id, company_id, email)
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return {"access_token": token, "user": user}

@api.post("/auth/login")
async def login(body: LoginBody, request: Request):
    email = body.email.lower()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"
    attempt = await db.login_attempts.find_one({"identifier": identifier})
    if attempt and attempt.get("count", 0) >= 5:
        locked_until = datetime.fromisoformat(attempt["locked_until"])
        if datetime.now(timezone.utc) < locked_until:
            raise HTTPException(status_code=429, detail="Too many attempts. Try again in 15 minutes.")

    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        count = (attempt.get("count", 0) if attempt else 0) + 1
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {"$set": {"identifier": identifier, "count": count,
                      "locked_until": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()}},
            upsert=True,
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await db.login_attempts.delete_one({"identifier": identifier})
    token = create_access_token(user["id"], user["company_id"], email)
    safe = {k: v for k, v in user.items() if k not in ("_id", "password_hash")}
    return {"access_token": token, "user": safe}

@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user

# ---------------------------------------------------------------------------
# Catalog endpoints
# ---------------------------------------------------------------------------
@api.get("/products")
async def list_products(user: dict = Depends(get_current_user)):
    products = await db.products.find({"company_id": user["company_id"]}, {"_id": 0}).sort("name", 1).to_list(2000)
    return products

@api.post("/products")
async def create_product(body: ProductBody, user: dict = Depends(get_current_user)):
    doc = {"id": str(uuid.uuid4()), "company_id": user["company_id"], **body.model_dump(), "created_at": now_iso()}
    await db.products.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.put("/products/{product_id}")
async def update_product(product_id: str, body: ProductBody, user: dict = Depends(get_current_user)):
    res = await db.products.update_one(
        {"id": product_id, "company_id": user["company_id"]}, {"$set": body.model_dump()})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    doc = await db.products.find_one({"id": product_id}, {"_id": 0})
    return doc

@api.delete("/products/{product_id}")
async def delete_product(product_id: str, user: dict = Depends(get_current_user)):
    await db.products.delete_one({"id": product_id, "company_id": user["company_id"]})
    return {"ok": True}

@api.post("/products/import")
async def import_products(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    content = await file.read()
    df = _read_tabular(content, file.filename)
    cols = {c.lower().strip(): c for c in df.columns}
    inserted = 0
    for _, row in df.iterrows():
        name = str(row.get(cols.get("name", ""), "")).strip()
        if not name or name.lower() == "nan":
            continue
        aliases_raw = str(row.get(cols.get("aliases", ""), ""))
        aliases = [a.strip() for a in aliases_raw.split(",") if a.strip() and a.strip().lower() != "nan"]
        try:
            price = float(row.get(cols.get("price", ""), 0) or 0)
        except (ValueError, TypeError):
            price = 0.0
        await db.products.insert_one({
            "id": str(uuid.uuid4()), "company_id": user["company_id"], "name": name,
            "sku": str(row.get(cols.get("sku", ""), "") or "").strip(),
            "category": str(row.get(cols.get("category", ""), "General") or "General").strip(),
            "unit": str(row.get(cols.get("unit", ""), "unit") or "unit").strip(),
            "pack_size": str(row.get(cols.get("pack_size", ""), "") or "").strip(),
            "price": price, "aliases": aliases, "created_at": now_iso(),
        })
        inserted += 1
    return {"inserted": inserted}

# ---------------------------------------------------------------------------
# Ingestion layer
# ---------------------------------------------------------------------------
def _read_tabular(content: bytes, filename: str) -> pd.DataFrame:
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(content))
    return pd.read_excel(io.BytesIO(content))

def _extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return "\n".join((page.extract_text() or "") for page in reader.pages)

# ---------------------------------------------------------------------------
# AI extraction pipeline
# ---------------------------------------------------------------------------
def _build_catalog_context(products: List[dict]) -> str:
    lines = []
    for p in products:
        aliases = ", ".join(p.get("aliases", []))
        lines.append(
            f"- id={p['id']} | sku={p.get('sku','')} | name={p['name']} | unit={p.get('unit','')} "
            f"| pack={p.get('pack_size','')} | price={p.get('price',0)} | aliases=[{aliases}]"
        )
    return "\n".join(lines)

EXTRACTION_SYSTEM = """You are Ordia's expert order-entry assistant for a food wholesaler.
You read messy incoming orders (WhatsApp, email, PDFs, spreadsheets, photos of handwritten notes)
and convert them into clean structured order data.

You understand abbreviations, spelling mistakes, multilingual text, packaging conversions and aliases.
Match every requested item to the company product catalog provided. Use the catalog `id` for matches.

Return ONLY valid JSON (no markdown, no commentary) with this exact shape:
{
  "customer_name": string | null,
  "delivery_date": string | null,
  "notes": string | null,
  "line_items": [
    {
      "raw_text": string,          // the original text for this line
      "quantity": number,
      "unit": string,              // e.g. case, box, kg, bag
      "matched_product_id": string | null,  // catalog id, or null if no confident match
      "matched_sku": string | null,
      "matched_name": string | null,
      "price": number,             // unit price from catalog, else 0
      "confidence": number,        // 0..1 how sure you are of the product match
      "needs_review": boolean      // true if confidence < 0.8 or ambiguous
    }
  ]
}
Rules:
- If a product cannot be confidently matched, set matched fields null, confidence low, needs_review true.
- Always include every distinct item the customer asked for.
- Never invent items not present in the source text.
"""

async def run_extraction(source_text: Optional[str], image_b64: Optional[str], products: List[dict]) -> dict:
    catalog = _build_catalog_context(products)
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"extract-{uuid.uuid4()}",
        system_message=EXTRACTION_SYSTEM,
    ).with_model("anthropic", "claude-sonnet-4-6")

    prompt = f"COMPANY PRODUCT CATALOG:\n{catalog}\n\n"
    if source_text:
        prompt += f"INCOMING ORDER TEXT:\n{source_text}\n\nExtract the structured order now."
    else:
        prompt += "The incoming order is in the attached image. Extract the structured order now."

    file_contents = [ImageContent(image_base64=image_b64)] if image_b64 else None
    message = UserMessage(text=prompt, file_contents=file_contents)
    response = await chat.send_message(message)

    text = response.strip() if isinstance(response, str) else str(response)
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip().rstrip("`").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        data = json.loads(text[start:end + 1]) if start != -1 and end != -1 else {"line_items": []}

    # normalize line items
    items = []
    for it in data.get("line_items", []):
        items.append({
            "id": str(uuid.uuid4()),
            "raw_text": str(it.get("raw_text", "")),
            "quantity": float(it.get("quantity") or 1),
            "unit": str(it.get("unit") or "unit"),
            "matched_product_id": it.get("matched_product_id"),
            "matched_sku": it.get("matched_sku"),
            "matched_name": it.get("matched_name"),
            "price": float(it.get("price") or 0),
            "confidence": float(it.get("confidence") or 0),
            "needs_review": bool(it.get("needs_review", True)),
        })
    return {
        "customer_name": data.get("customer_name"),
        "delivery_date": data.get("delivery_date"),
        "notes": data.get("notes"),
        "line_items": items,
    }

# ---------------------------------------------------------------------------
# Order endpoints
# ---------------------------------------------------------------------------
@api.post("/orders/extract")
async def extract_order(
    request: Request,
    source_type: str = Form(...),
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    user = await get_current_user(request)
    products = await db.products.find({"company_id": user["company_id"]}, {"_id": 0}).to_list(2000)

    source_text = None
    image_b64 = None
    source_preview = ""

    if source_type == "text":
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")
        source_text = text
        source_preview = text
    elif source_type == "file":
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        content = await file.read()
        fname = (file.filename or "").lower()
        if fname.endswith((".csv", ".xlsx", ".xls")):
            df = _read_tabular(content, fname)
            source_text = df.to_csv(index=False)
            source_preview = source_text
        elif fname.endswith(".pdf"):
            source_text = _extract_pdf_text(content)
            source_preview = source_text or "(scanned PDF — no embedded text)"
            if not source_text.strip():
                raise HTTPException(status_code=400, detail="Could not read text from this PDF. Try an image instead.")
        elif fname.endswith((".png", ".jpg", ".jpeg", ".webp")):
            image_b64 = base64.b64encode(content).decode("utf-8")
            source_preview = f"[Image: {file.filename}]"
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
    else:
        raise HTTPException(status_code=400, detail="Invalid source_type")

    extracted = await run_extraction(source_text, image_b64, products)

    order_id = str(uuid.uuid4())
    review_count = sum(1 for i in extracted["line_items"] if i["needs_review"])
    order = {
        "id": order_id,
        "company_id": user["company_id"],
        "created_by": user["id"],
        "source_type": source_type,
        "source_preview": source_preview[:5000],
        "customer_name": extracted["customer_name"],
        "delivery_date": extracted["delivery_date"],
        "notes": extracted["notes"],
        "line_items": extracted["line_items"],
        "status": "needs_review" if review_count else "ready",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.orders.insert_one(dict(order))
    order.pop("_id", None)
    return order

@api.get("/orders")
async def list_orders(user: dict = Depends(get_current_user)):
    orders = await db.orders.find({"company_id": user["company_id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return orders

@api.get("/orders/{order_id}")
async def get_order(order_id: str, user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id, "company_id": user["company_id"]}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@api.put("/orders/{order_id}")
async def update_order(order_id: str, body: OrderUpdate, user: dict = Depends(get_current_user)):
    update = {k: v for k, v in body.model_dump().items() if v is not None}
    if "line_items" in update:
        update["line_items"] = [dict(i) for i in update["line_items"]]
    update["updated_at"] = now_iso()
    res = await db.orders.update_one(
        {"id": order_id, "company_id": user["company_id"]}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    return order

@api.post("/orders/{order_id}/validate")
async def validate_order(order_id: str, user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id, "company_id": user["company_id"]}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    await db.orders.update_one(
        {"id": order_id}, {"$set": {"status": "validated", "updated_at": now_iso()}})
    order["status"] = "validated"
    return order

@api.delete("/orders/{order_id}")
async def delete_order(order_id: str, user: dict = Depends(get_current_user)):
    await db.orders.delete_one({"id": order_id, "company_id": user["company_id"]})
    return {"ok": True}

@api.get("/orders/{order_id}/export")
async def export_order(order_id: str, format: str = "json", user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id, "company_id": user["company_id"]}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    await db.orders.update_one(
        {"id": order_id}, {"$set": {"status": "exported", "updated_at": now_iso()}})

    if format == "csv":
        rows = []
        for i in order["line_items"]:
            rows.append({
                "sku": i.get("matched_sku") or "", "product": i.get("matched_name") or i.get("raw_text"),
                "quantity": i.get("quantity"), "unit": i.get("unit"),
                "unit_price": i.get("price"), "line_total": round((i.get("price") or 0) * (i.get("quantity") or 0), 2),
            })
        df = pd.DataFrame(rows)
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]), media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=order-{order_id[:8]}.csv"})

    payload = {
        "order_id": order["id"], "customer_name": order.get("customer_name"),
        "delivery_date": order.get("delivery_date"), "notes": order.get("notes"),
        "line_items": [
            {"sku": i.get("matched_sku"), "product": i.get("matched_name") or i.get("raw_text"),
             "quantity": i.get("quantity"), "unit": i.get("unit"),
             "unit_price": i.get("price"),
             "line_total": round((i.get("price") or 0) * (i.get("quantity") or 0), 2)}
            for i in order["line_items"]
        ],
    }
    body = json.dumps(payload, indent=2)
    return StreamingResponse(
        iter([body]), media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=order-{order_id[:8]}.json"})

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@api.get("/dashboard/stats")
async def dashboard_stats(user: dict = Depends(get_current_user)):
    cid = user["company_id"]
    orders = await db.orders.find({"company_id": cid}, {"_id": 0}).sort("created_at", -1).to_list(500)
    total = len(orders)
    needs_review = sum(1 for o in orders if o["status"] == "needs_review")
    processed = sum(1 for o in orders if o["status"] in ("validated", "exported"))
    total_lines = sum(len(o.get("line_items", [])) for o in orders)
    all_conf = [i.get("confidence", 0) for o in orders for i in o.get("line_items", [])]
    avg_conf = round(sum(all_conf) / len(all_conf) * 100) if all_conf else 0
    hours_saved = round(total_lines * 1.5 / 60, 1)  # ~1.5 min manual entry per line
    return {
        "total_orders": total,
        "needs_review": needs_review,
        "processed": processed,
        "accuracy": avg_conf,
        "hours_saved": hours_saved,
        "products": await db.products.count_documents({"company_id": cid}),
        "recent": orders[:8],
    }

# ---------------------------------------------------------------------------
# App wiring
# ---------------------------------------------------------------------------
app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.products.create_index("company_id")
    await db.orders.create_index("company_id")
    await db.login_attempts.create_index("identifier")
    logger.info("Ordia API ready.")

@app.on_event("shutdown")
async def shutdown():
    client.close()
