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
import re
import json
import uuid
import base64
import asyncio
import logging
import secrets
import tempfile
import smtplib
import imaplib
import email as email_lib
from email.header import decode_header
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import bcrypt
import jwt
import pandas as pd
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors as rl_colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
from emergentintegrations.llm.openai import OpenAISpeechToText

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

def history_entry(action: str, by: str = "system", detail: str = "") -> dict:
    return {"ts": now_iso(), "action": action, "by": by, "detail": detail}

def _order_rows(order: dict) -> List[dict]:
    rows = []
    for i in order.get("line_items", []):
        rows.append({
            "sku": i.get("matched_sku") or "",
            "product": i.get("matched_name") or i.get("raw_text") or "",
            "quantity": i.get("quantity"),
            "unit": i.get("unit"),
            "unit_price": round(i.get("price") or 0, 2),
            "line_total": round((i.get("price") or 0) * (i.get("quantity") or 0), 2),
        })
    return rows

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
        "password_hash": hash_password(body.password), "role": "owner", "created_at": now_iso(),
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

AUDIO_EXTS = (".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg")

async def transcribe_audio(content: bytes, filename: str) -> str:
    """Transcribe a voice message to text using OpenAI Whisper (whisper-1)."""
    suffix = os.path.splitext(filename or "audio.mp3")[1] or ".mp3"
    stt = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(content)
        tmp.flush()
        tmp.seek(0)
        with open(tmp.name, "rb") as audio_file:
            response = await stt.transcribe(file=audio_file, model="whisper-1", response_format="json")
    return (response.text or "").strip()

# ---------------------------------------------------------------------------
# AI extraction pipeline + Learning loop
# ---------------------------------------------------------------------------
_UNIT_WORDS = {
    "case", "cases", "box", "boxes", "bag", "bags", "sack", "sacks", "tray", "trays",
    "kg", "g", "gr", "lt", "l", "ml", "pack", "packs", "ct", "unit", "units",
    "cassa", "casse", "scatola", "scatole", "sacco", "sacchi", "vassoio", "vassoi",
    "cartone", "cartoni", "confezione", "confezioni", "pz", "pezzi", "pezzo", "unita", "unità", "x", "di", "da", "of",
}

def normalize_phrase(text: str) -> str:
    t = (text or "").lower()
    t = re.sub(r"[^a-zàèéìòùáéíóú0-9\s]", " ", t)
    tokens = [w for w in t.split() if not w.isdigit() and w not in _UNIT_WORDS]
    return " ".join(tokens).strip()

async def get_learned_aliases(company_id: str) -> List[dict]:
    return await db.learned_aliases.find({"company_id": company_id}, {"_id": 0}).to_list(5000)

async def learn_from_order(company_id: str, order: dict):
    """Every confirmed line becomes a persistent phrase→product mapping so the
    AI never repeats the same matching mistake for this company."""
    customer = order.get("customer_name")
    for it in order.get("line_items", []):
        pid = it.get("matched_product_id")
        phrase = normalize_phrase(it.get("raw_text", ""))
        if not pid or not phrase or len(phrase) < 2:
            continue
        await db.learned_aliases.update_one(
            {"company_id": company_id, "phrase": phrase},
            {"$set": {"product_id": pid, "sku": it.get("matched_sku"), "name": it.get("matched_name"),
                      "customer_name": customer, "updated_at": now_iso()},
             "$inc": {"count": 1},
             "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": now_iso()}},
            upsert=True,
        )

def _build_catalog_context(products: List[dict], learned_by_pid: dict = None) -> str:
    learned_by_pid = learned_by_pid or {}
    lines = []
    for p in products:
        aliases = list(p.get("aliases", [])) + learned_by_pid.get(p["id"], [])
        lines.append(
            f"- id={p['id']} | sku={p.get('sku','')} | name={p['name']} | unit={p.get('unit','')} "
            f"| pack={p.get('pack_size','')} | price={p.get('price',0)} | aliases=[{', '.join(aliases)}]"
        )
    return "\n".join(lines)

EXTRACTION_SYSTEM = """You are Ordia's expert order-entry assistant for a food wholesaler.
You read messy incoming orders (WhatsApp, email, PDFs, spreadsheets, photos of handwritten notes)
and convert them into clean structured order data.

You understand abbreviations, spelling mistakes, multilingual text, packaging conversions and aliases.
Match every requested item to the company product catalog provided. Use the catalog `id` for matches.
The catalog aliases include phrases previously confirmed by human operators — treat them as strong signals.

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

async def run_extraction(source_text: Optional[str], image_b64: Optional[str], products: List[dict],
                         learned: List[dict] = None) -> dict:
    learned = learned or []
    products_by_id = {p["id"]: p for p in products}
    learned_by_pid = {}
    phrase_to_pid = {}
    for la in learned:
        if la.get("product_id") in products_by_id:
            learned_by_pid.setdefault(la["product_id"], []).append(la["phrase"])
            phrase_to_pid[la["phrase"]] = la["product_id"]

    catalog = _build_catalog_context(products, learned_by_pid)
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

    # normalize line items + apply learned deterministic overrides
    items = []
    for it in data.get("line_items", []):
        raw = str(it.get("raw_text", ""))
        item = {
            "id": str(uuid.uuid4()),
            "raw_text": raw,
            "quantity": float(it.get("quantity") or 1),
            "unit": str(it.get("unit") or "unit"),
            "matched_product_id": it.get("matched_product_id"),
            "matched_sku": it.get("matched_sku"),
            "matched_name": it.get("matched_name"),
            "price": float(it.get("price") or 0),
            "confidence": float(it.get("confidence") or 0),
            "needs_review": bool(it.get("needs_review", True)),
            "learned": False,
        }
        np = normalize_phrase(raw)
        if np in phrase_to_pid:
            p = products_by_id[phrase_to_pid[np]]
            item.update({
                "matched_product_id": p["id"], "matched_sku": p.get("sku"), "matched_name": p["name"],
                "price": p.get("price", 0), "unit": p.get("unit", item["unit"]),
                "confidence": max(item["confidence"], 0.99), "needs_review": False, "learned": True,
            })
        items.append(item)
    return {
        "customer_name": data.get("customer_name"),
        "delivery_date": data.get("delivery_date"),
        "notes": data.get("notes"),
        "line_items": items,
    }

# ---------------------------------------------------------------------------
# Order endpoints
# ---------------------------------------------------------------------------
DEFAULT_AUTOMATIONS = {
    "auto_confirm_enabled": False,
    "confidence_threshold": 0.9,
    "hold_new_customers": True,
}

async def get_automations(company_id: str) -> dict:
    c = await db.companies.find_one({"id": company_id}, {"_id": 0, "settings": 1})
    a = (c or {}).get("settings", {}).get("automations", {})
    return {**DEFAULT_AUTOMATIONS, **a}

async def ingest_order(company_id: str, source_type: str, source_preview: str,
                       source_text: Optional[str] = None, image_b64: Optional[str] = None,
                       created_by: str = "system", external_id: Optional[str] = None,
                       source_meta: Optional[dict] = None) -> Optional[dict]:
    """Single entry point for the whole order pipeline used by every channel
    (manual upload, email, WhatsApp, future plugins):
    Input -> AI extraction -> Catalog match -> Learning loop -> draft order.
    Returns the created order, or None if it was a duplicate (idempotent by external_id)."""
    if external_id:
        dup = await db.orders.find_one({"company_id": company_id, "external_id": external_id}, {"_id": 0})
        if dup:
            logger.info("Skipping duplicate order external_id=%s", external_id)
            return None
    products = await db.products.find({"company_id": company_id}, {"_id": 0}).to_list(2000)
    learned = await get_learned_aliases(company_id)
    extracted = await run_extraction(source_text, image_b64, products, learned)
    items = extracted["line_items"]
    review_count = sum(1 for i in items if i["needs_review"])

    # Automation: auto-confirm high-confidence, fully-matched orders.
    autom = await get_automations(company_id)
    status = "needs_review" if review_count else "ready"
    auto_confirmed = False
    if autom["auto_confirm_enabled"] and items and review_count == 0:
        all_matched = all(i.get("matched_product_id") for i in items)
        conf_ok = all((i.get("confidence") or 0) >= autom["confidence_threshold"] for i in items)
        is_new = False
        if autom["hold_new_customers"] and extracted.get("customer_name"):
            prev = await db.orders.find_one(
                {"company_id": company_id, "customer_name": extracted["customer_name"]}, {"_id": 0, "id": 1})
            is_new = prev is None
        if all_matched and conf_ok and not is_new:
            status = "validated"
            auto_confirmed = True

    history = [history_entry("Ordine estratto", created_by, f"Fonte: {source_type}")]
    if auto_confirmed:
        history.append(history_entry("Confermato automaticamente", "automation",
                                     f"Confidenza ≥ {int(autom['confidence_threshold'] * 100)}%"))
    order = {
        "id": str(uuid.uuid4()), "company_id": company_id, "created_by": created_by,
        "source_type": source_type, "source_preview": (source_preview or "")[:5000],
        "external_id": external_id, "source_meta": source_meta or {},
        "customer_name": extracted["customer_name"], "delivery_date": extracted["delivery_date"],
        "notes": extracted["notes"], "line_items": items,
        "status": status,
        "auto_confirmed": auto_confirmed,
        "created_at": now_iso(), "updated_at": now_iso(),
        "history": history,
    }
    await db.orders.insert_one(dict(order))
    order.pop("_id", None)
    if auto_confirmed:
        await learn_from_order(company_id, order)
    logger.info("Ingested order %s via %s (%d items, %d need review, auto_confirmed=%s)",
                order["id"], source_type, len(items), review_count, auto_confirmed)
    return order

@api.post("/orders/extract")
async def extract_order(
    request: Request,
    source_type: str = Form(...),
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    user = await get_current_user(request)

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
            source_preview = f"[Immagine: {file.filename}]"
        elif fname.endswith(AUDIO_EXTS):
            transcript = await transcribe_audio(content, fname)
            if not transcript.strip():
                raise HTTPException(status_code=400, detail="Impossibile trascrivere l'audio. Riprova con un file più chiaro.")
            source_text = transcript
            source_preview = f"[Messaggio vocale trascritto]\n{transcript}"
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
    else:
        raise HTTPException(status_code=400, detail="Invalid source_type")

    order = await ingest_order(
        user["company_id"], source_type, source_preview,
        source_text=source_text, image_b64=image_b64, created_by=user["id"])
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
        {"id": order_id, "company_id": user["company_id"]},
        {"$set": update, "$push": {"history": history_entry("Modifiche salvate", user["id"])}})
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
        {"id": order_id}, {"$set": {"status": "validated", "updated_at": now_iso()},
                           "$push": {"history": history_entry("Ordine confermato", user["id"])}})
    order["status"] = "validated"
    await learn_from_order(user["company_id"], order)  # every confirmed line teaches Ordia
    return order

@api.get("/learning")
async def list_learning(user: dict = Depends(get_current_user)):
    items = await db.learned_aliases.find(
        {"company_id": user["company_id"]}, {"_id": 0}).sort("count", -1).to_list(2000)
    return items

@api.delete("/learning/{alias_id}")
async def delete_learning(alias_id: str, user: dict = Depends(get_current_user)):
    await db.learned_aliases.delete_one({"id": alias_id, "company_id": user["company_id"]})
    return {"ok": True}

@api.delete("/orders/{order_id}")
async def delete_order(order_id: str, user: dict = Depends(get_current_user)):
    await db.orders.delete_one({"id": order_id, "company_id": user["company_id"]})
    return {"ok": True}

@api.get("/orders/{order_id}/export")
async def export_order(order_id: str, format: str = "json", user: dict = Depends(get_current_user)):
    from xml.sax.saxutils import escape as _esc
    order = await db.orders.find_one({"id": order_id, "company_id": user["company_id"]}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    rows = _order_rows(order)
    total = round(sum(r["line_total"] for r in rows), 2)
    fname = f"ordine-{order_id[:8]}"

    # Build the file bytes FIRST; only mutate order status once we know it succeeded.
    if format == "csv":
        df = pd.DataFrame(rows)
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        content, media_type, ext = buf.getvalue(), "text/csv", "csv"

    elif format in ("xlsx", "excel"):
        df = pd.DataFrame(rows)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Ordine")
        content = buf.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"

    elif format == "pdf":
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=24 * mm,
                                leftMargin=18 * mm, rightMargin=18 * mm, bottomMargin=18 * mm)
        styles = getSampleStyleSheet()
        navy = rl_colors.HexColor("#0B1E3B")
        title_style = ParagraphStyle("t", parent=styles["Title"], textColor=navy, fontSize=20, spaceAfter=2)
        meta_style = ParagraphStyle("m", parent=styles["Normal"], textColor=rl_colors.HexColor("#4B5563"), fontSize=9)
        elements = [Paragraph("ORDIA", title_style),
                    Paragraph("Conferma d'ordine", ParagraphStyle("s", parent=styles["Normal"], fontSize=11, spaceAfter=10))]
        cust = _esc(order.get("customer_name") or "Cliente sconosciuto")
        delivery = _esc(order.get("delivery_date") or "—")
        elements.append(Paragraph(f"<b>Cliente:</b> {cust}", meta_style))
        elements.append(Paragraph(f"<b>Consegna:</b> {delivery}", meta_style))
        elements.append(Paragraph(f"<b>ID ordine:</b> {order_id[:8]}", meta_style))
        elements.append(Spacer(1, 10))
        data = [["SKU", "Prodotto", "Q.tà", "Unità", "Prezzo", "Totale"]]
        for r in rows:
            data.append([r["sku"], r["product"], str(r["quantity"]), r["unit"],
                         f"€{r['unit_price']:.2f}", f"€{r['line_total']:.2f}"])
        data.append(["", "", "", "", "Totale", f"€{total:.2f}"])
        table = Table(data, colWidths=[55, 190, 40, 50, 55, 60], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), navy),
            ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -2), 0.4, rl_colors.HexColor("#E5E7EB")),
            ("BACKGROUND", (0, -1), (-1, -1), rl_colors.HexColor("#F3F4F6")),
            ("FONTNAME", (-2, -1), (-1, -1), "Helvetica-Bold"),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(table)
        if order.get("notes"):
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(f"<b>Note:</b> {_esc(order['notes'])}", meta_style))
        doc.build(elements)
        content, media_type, ext = buf.getvalue(), "application/pdf", "pdf"

    else:
        payload = {
            "order_id": order["id"], "customer_name": order.get("customer_name"),
            "delivery_date": order.get("delivery_date"), "notes": order.get("notes"),
            "line_items": rows, "total": total,
        }
        content = json.dumps(payload, indent=2, ensure_ascii=False)
        media_type, ext = "application/json", "json"

    await db.orders.update_one(
        {"id": order_id}, {"$set": {"status": "exported", "updated_at": now_iso()},
                           "$push": {"history": history_entry(f"Esportato ({ext.upper()})", user["id"])}})
    return StreamingResponse(
        iter([content]), media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={fname}.{ext}"})

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

def _order_total(o: dict) -> float:
    return round(sum((i.get("price") or 0) * (i.get("quantity") or 0) for i in o.get("line_items", [])), 2)

def _aggregate_customers(orders: List[dict]) -> List[dict]:
    by_name = {}
    for o in orders:
        name = (o.get("customer_name") or "Sconosciuto").strip() or "Sconosciuto"
        c = by_name.setdefault(name, {"name": name, "orders": 0, "volume": 0.0, "last_order": None, "products": {}})
        c["orders"] += 1
        c["volume"] += _order_total(o)
        if not c["last_order"] or o["created_at"] > c["last_order"]:
            c["last_order"] = o["created_at"]
        for i in o.get("line_items", []):
            nm = i.get("matched_name")
            if nm:
                c["products"][nm] = c["products"].get(nm, 0) + 1
    result = []
    for c in by_name.values():
        fav = sorted(c["products"].items(), key=lambda x: -x[1])[:3]
        result.append({**c, "volume": round(c["volume"], 2),
                       "favorite_products": [f[0] for f in fav], "products": None})
    result.sort(key=lambda x: x["last_order"] or "", reverse=True)
    return result

@api.get("/command-center")
async def command_center(user: dict = Depends(get_current_user)):
    cid = user["company_id"]
    orders = await db.orders.find({"company_id": cid}, {"_id": 0}).sort("created_at", -1).to_list(500)
    today = datetime.now(timezone.utc).date().isoformat()
    todays = [o for o in orders if (o.get("created_at") or "").startswith(today)]
    auto = sum(1 for o in todays if o["status"] in ("ready", "validated", "exported"))
    review_today = sum(1 for o in todays if o["status"] == "needs_review")
    to_review = [o for o in orders if o["status"] == "needs_review"][:6]
    learned_week = await db.learned_aliases.count_documents({"company_id": cid})
    customers = _aggregate_customers(orders)

    notifications = []
    if review_today or to_review:
        notifications.append({"type": "review", "text": f"{len(to_review)} ordini attendono la tua conferma."})
    low_conf = sum(1 for o in orders for i in o.get("line_items", []) if i.get("confidence", 1) < 0.6)
    if low_conf:
        notifications.append({"type": "warning", "text": f"{low_conf} articoli con bassa confidenza da controllare."})
    if learned_week:
        notifications.append({"type": "learning", "text": f"Ordia ha appreso {learned_week} regole dai tuoi ordini."})
    repeat = [c for c in customers if c["orders"] >= 2][:1]
    if repeat:
        notifications.append({"type": "insight", "text": f"{repeat[0]['name']} è un cliente ricorrente ({repeat[0]['orders']} ordini)."})

    return {
        "today": {"total": len(todays), "auto": auto, "review": review_today},
        "to_review": to_review,
        "recent_activity": orders[:8],
        "notifications": notifications,
        "recent_customers": customers[:6],
        "totals": {"orders": len(orders), "customers": len(customers)},
    }

@api.get("/search")
async def global_search(q: str = "", user: dict = Depends(get_current_user)):
    cid = user["company_id"]
    ql = q.strip().lower()
    if len(ql) < 1:
        return {"orders": [], "products": [], "customers": []}
    orders = await db.orders.find({"company_id": cid}, {"_id": 0}).sort("created_at", -1).to_list(500)
    products = await db.products.find({"company_id": cid}, {"_id": 0}).to_list(2000)
    o_hits = [{"id": o["id"], "customer_name": o.get("customer_name"), "status": o["status"],
               "created_at": o["created_at"]}
              for o in orders
              if ql in (o.get("customer_name") or "").lower() or ql in o["id"].lower()
              or ql in (o.get("external_id") or "").lower()][:6]
    p_hits = [{"id": p["id"], "name": p["name"], "sku": p.get("sku"), "price": p.get("price")}
              for p in products
              if ql in p["name"].lower() or ql in (p.get("sku") or "").lower()
              or any(ql in a.lower() for a in p.get("aliases", []))][:6]
    customers = _aggregate_customers(orders)
    c_hits = [c for c in customers if ql in c["name"].lower()][:6]
    return {"orders": o_hits, "products": p_hits, "customers": c_hits}

@api.get("/customers")
async def list_customers(user: dict = Depends(get_current_user)):
    orders = await db.orders.find({"company_id": user["company_id"]}, {"_id": 0}).to_list(500)
    return _aggregate_customers(orders)

@api.get("/customers/{name}")
async def customer_detail(name: str, user: dict = Depends(get_current_user)):
    orders = await db.orders.find({"company_id": user["company_id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    mine = [o for o in orders if (o.get("customer_name") or "Sconosciuto") == name]
    if not mine:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    agg = _aggregate_customers(mine)[0]
    insights = []
    if agg["orders"] >= 2:
        insights.append(f"Cliente ricorrente con {agg['orders']} ordini per €{agg['volume']:.2f} totali.")
    if agg["favorite_products"]:
        insights.append(f"Ordina spesso: {', '.join(agg['favorite_products'])}.")
    insights.append("Suggerimento: proponi un riordino dei prodotti abituali.")
    return {"customer": agg, "orders": mine, "insights": insights}

# ---------------------------------------------------------------------------
# Roles, company settings & team management
# ---------------------------------------------------------------------------
ROLES = ["owner", "admin", "sales", "operator", "warehouse", "readonly"]
PRIVILEGED = {"owner", "admin"}
GRAPH_VERSION = "v21.0"

def require_privileged(user: dict):
    if user.get("role") not in PRIVILEGED:
        raise HTTPException(status_code=403, detail="Solo Owner/Admin possono eseguire questa azione.")

def mask_secret(t: Optional[str]) -> str:
    if not t:
        return ""
    return (t[:6] + "…" + t[-4:]) if len(t) > 12 else "••••••"

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    vat: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    phone: Optional[str] = None

class TeamMemberCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = "operator"

class RoleUpdate(BaseModel):
    role: str

class AutomationSettings(BaseModel):
    auto_confirm_enabled: bool = False
    confidence_threshold: float = Field(0.9, ge=0.5, le=1.0)
    hold_new_customers: bool = True

@api.get("/automations")
async def get_automations_ep(user: dict = Depends(get_current_user)):
    return await get_automations(user["company_id"])

@api.put("/automations")
async def update_automations_ep(body: AutomationSettings, user: dict = Depends(get_current_user)):
    require_privileged(user)
    await db.companies.update_one(
        {"id": user["company_id"]}, {"$set": {"settings.automations": body.model_dump()}})
    return await get_automations(user["company_id"])

@api.get("/company")
async def get_company(user: dict = Depends(get_current_user)):
    company = await db.companies.find_one({"id": user["company_id"]}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@api.put("/company")
async def update_company(body: CompanyUpdate, user: dict = Depends(get_current_user)):
    require_privileged(user)
    update = {k: v for k, v in body.model_dump().items() if v is not None}
    await db.companies.update_one({"id": user["company_id"]}, {"$set": update})
    return await db.companies.find_one({"id": user["company_id"]}, {"_id": 0})

@api.get("/team")
async def list_team(user: dict = Depends(get_current_user)):
    members = await db.users.find(
        {"company_id": user["company_id"]}, {"_id": 0, "password_hash": 0}).sort("created_at", 1).to_list(500)
    return members

@api.post("/team")
async def create_team_member(body: TeamMemberCreate, user: dict = Depends(get_current_user)):
    require_privileged(user)
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail="Ruolo non valido")
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email già registrata")
    doc = {
        "id": str(uuid.uuid4()), "company_id": user["company_id"], "email": email,
        "name": body.name, "password_hash": hash_password(body.password), "role": body.role,
        "created_at": now_iso(),
    }
    await db.users.insert_one(dict(doc))
    doc.pop("password_hash", None)
    return doc

@api.put("/team/{member_id}/role")
async def update_member_role(member_id: str, body: RoleUpdate, user: dict = Depends(get_current_user)):
    require_privileged(user)
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail="Ruolo non valido")
    res = await db.users.update_one(
        {"id": member_id, "company_id": user["company_id"]}, {"$set": {"role": body.role}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Membro non trovato")
    return await db.users.find_one({"id": member_id}, {"_id": 0, "password_hash": 0})

@api.delete("/team/{member_id}")
async def delete_member(member_id: str, user: dict = Depends(get_current_user)):
    require_privileged(user)
    if member_id == user["id"]:
        raise HTTPException(status_code=400, detail="Non puoi eliminare te stesso")
    await db.users.delete_one({"id": member_id, "company_id": user["company_id"]})
    return {"ok": True}

# ---------------------------------------------------------------------------
# Integrations — provider-based, ERP-agnostic order channels & export
# ---------------------------------------------------------------------------
class WhatsAppConnect(BaseModel):
    label: str = "WhatsApp Business"
    access_token: str
    phone_number_id: str
    waba_id: str
    app_secret: Optional[str] = None
    verify_token: Optional[str] = None

class WhatsAppTest(BaseModel):
    to: str
    text: str = "Ciao! Questo è un messaggio di prova da Ordia. La connessione WhatsApp funziona. ✅"

class EmailConnect(BaseModel):
    inbound_provider: Optional[str] = None  # gmail | m365 | imap | forwarding
    inbound_host: Optional[str] = None
    inbound_email: Optional[str] = None
    inbound_password: Optional[str] = None
    outbound_enabled: bool = False
    outbound_host: Optional[str] = None
    outbound_port: int = 587
    outbound_email: Optional[str] = None
    outbound_password: Optional[str] = None

class ERPConnect(BaseModel):
    provider: str = "webhook"        # webhook | rest | file
    format: str = "json"             # json | csv | xml
    endpoint_url: Optional[str] = None
    method: str = "POST"
    auth_header_name: Optional[str] = None
    auth_header_value: Optional[str] = None

IMAP_HOSTS = {"gmail": "imap.gmail.com", "m365": "outlook.office365.com"}
SMTP_HOSTS = {"gmail": "smtp.gmail.com", "m365": "smtp.office365.com"}

async def _get_integration(company_id: str, itype: str, account_id: Optional[str] = None):
    q = {"company_id": company_id, "type": itype}
    if account_id:
        q["id"] = account_id
    return await db.integrations.find_one(q, {"_id": 0})

def _whatsapp_public(doc: dict) -> dict:
    d = dict(doc)
    d["access_token"] = mask_secret(doc.get("access_token"))
    d["app_secret"] = mask_secret(doc.get("app_secret"))
    return d

# ---- Integrations overview / onboarding checklist -------------------------
@api.get("/integrations")
async def integrations_overview(user: dict = Depends(get_current_user)):
    cid = user["company_id"]
    wa = await db.integrations.find({"company_id": cid, "type": "whatsapp"}, {"_id": 0}).to_list(50)
    email = await _get_integration(cid, "email")
    erp = await _get_integration(cid, "erp")
    products = await db.products.count_documents({"company_id": cid})
    team = await db.users.count_documents({"company_id": cid})
    company = await db.companies.find_one({"id": cid}, {"_id": 0})
    wa_connected = any(a.get("status") == "connected" for a in wa)
    steps = [
        {"key": "company", "label": "Dati azienda", "done": bool(company and company.get("vat"))},
        {"key": "catalog", "label": "Catalogo prodotti", "done": products > 0},
        {"key": "whatsapp", "label": "WhatsApp Business", "done": wa_connected,
         "status": "connected" if wa_connected else ("pending" if wa else "not_configured")},
        {"key": "email", "label": "Email", "done": bool(email and email.get("status") == "connected"),
         "status": (email or {}).get("status", "not_configured")},
        {"key": "erp", "label": "Export ERP", "done": bool(erp and erp.get("status") == "connected"),
         "status": (erp or {}).get("status", "not_configured")},
        {"key": "team", "label": "Team", "done": team > 1},
    ]
    completed = sum(1 for s in steps if s["done"])
    return {
        "progress": round(completed / len(steps) * 100),
        "completed": completed, "total": len(steps), "steps": steps,
        "counts": {"whatsapp_accounts": len(wa), "products": products, "team": team},
    }

# ---- WhatsApp Business ----------------------------------------------------
@api.get("/integrations/whatsapp")
async def whatsapp_list(user: dict = Depends(get_current_user)):
    accounts = await db.integrations.find(
        {"company_id": user["company_id"], "type": "whatsapp"}, {"_id": 0}).to_list(50)
    return [_whatsapp_public(a) for a in accounts]

@api.post("/integrations/whatsapp")
async def whatsapp_save(body: WhatsAppConnect, user: dict = Depends(get_current_user)):
    require_privileged(user)
    doc = {
        "id": str(uuid.uuid4()), "company_id": user["company_id"], "type": "whatsapp",
        "label": body.label, "access_token": body.access_token, "phone_number_id": body.phone_number_id,
        "waba_id": body.waba_id, "app_secret": body.app_secret,
        "verify_token": body.verify_token or secrets.token_urlsafe(16),
        "status": "pending", "display_phone_number": None, "verified_name": None,
        "last_error": None, "last_checked": None, "created_at": now_iso(),
    }
    await db.integrations.insert_one(dict(doc))
    return _whatsapp_public(doc)

@api.post("/integrations/whatsapp/{account_id}/validate")
async def whatsapp_validate(account_id: str, user: dict = Depends(get_current_user)):
    require_privileged(user)
    acc = await _get_integration(user["company_id"], "whatsapp", account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account non trovato")

    def _check():
        base = f"https://graph.facebook.com/{GRAPH_VERSION}"
        headers = {"Authorization": f"Bearer {acc['access_token']}"}
        steps = []
        # 1) token + phone number
        r1 = requests.get(f"{base}/{acc['phone_number_id']}",
                          headers=headers, params={"fields": "id,display_phone_number,verified_name"}, timeout=15)
        steps.append(("phone_number", r1.status_code, r1.text))
        if r1.status_code != 200:
            return {"ok": False, "stage": "phone_number", "code": r1.status_code, "body": r1.text, "steps": steps}
        phone = r1.json()
        # 2) WABA
        r2 = requests.get(f"{base}/{acc['waba_id']}", headers=headers, params={"fields": "id,name"}, timeout=15)
        steps.append(("waba", r2.status_code, r2.text))
        if r2.status_code != 200:
            return {"ok": False, "stage": "waba", "code": r2.status_code, "body": r2.text, "steps": steps}
        return {"ok": True, "phone": phone, "waba": r2.json(), "steps": steps}

    try:
        result = await asyncio.to_thread(_check)
    except Exception as e:  # network / DNS
        await db.integrations.update_one({"id": account_id}, {"$set": {
            "status": "error", "last_error": f"Errore di rete: {e}", "last_checked": now_iso()}})
        raise HTTPException(status_code=502, detail=f"Impossibile contattare Meta Graph API: {e}")

    if not result["ok"]:
        await db.integrations.update_one({"id": account_id}, {"$set": {
            "status": "error", "last_error": f"{result['stage']} (HTTP {result['code']})",
            "last_error_body": result["body"][:800], "last_checked": now_iso()}})
        return {"status": "error", "stage": result["stage"], "code": result["code"],
                "message": _wa_error_hint(result["code"], result["body"])}

    await db.integrations.update_one({"id": account_id}, {"$set": {
        "status": "connected", "display_phone_number": result["phone"].get("display_phone_number"),
        "verified_name": result["phone"].get("verified_name"), "last_error": None, "last_checked": now_iso()}})

    # Automation: subscribe our app to the WABA so inbound messages hit our webhook.
    def _subscribe():
        try:
            r = requests.post(
                f"https://graph.facebook.com/{GRAPH_VERSION}/{acc['waba_id']}/subscribed_apps",
                headers={"Authorization": f"Bearer {acc['access_token']}"}, timeout=15)
            return r.status_code, r.text
        except Exception as e:
            return 0, str(e)
    sub_code, sub_body = await asyncio.to_thread(_subscribe)
    subscribed = 200 <= sub_code < 300
    await db.integrations.update_one({"id": account_id}, {"$set": {
        "webhook_subscribed": subscribed, "webhook_sub_error": None if subscribed else sub_body[:300]}})
    return {"status": "connected", "phone": result["phone"], "waba": result["waba"],
            "webhook_subscribed": subscribed}

def _wa_error_hint(code: int, body: str) -> str:
    b = (body or "").lower()
    if code in (401, 190) or "expired" in b or "invalid oauth" in b:
        return "Access Token non valido o scaduto. Genera un token permanente (System User) in Meta Business Settings."
    if code == 403 or "permission" in b:
        return "Permessi insufficienti. Il token deve avere gli scope whatsapp_business_messaging e whatsapp_business_management."
    if code == 404 or "does not exist" in b or "unsupported" in b:
        return "Phone Number ID o WABA ID non trovato. Verifica gli ID in WhatsApp Manager."
    if "2388103" in b:
        return "Il numero non è registrato correttamente. Completa la registrazione del numero e la verifica business."
    return "Verifica ha fallito. Controlla credenziali, verifica business e registrazione del numero."

@api.post("/integrations/whatsapp/{account_id}/test-message")
async def whatsapp_test(account_id: str, body: WhatsAppTest, user: dict = Depends(get_current_user)):
    require_privileged(user)
    acc = await _get_integration(user["company_id"], "whatsapp", account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account non trovato")
    if acc.get("status") != "connected":
        raise HTTPException(status_code=400, detail="Connetti e valida l'account prima di inviare un test.")

    def _send():
        base = f"https://graph.facebook.com/{GRAPH_VERSION}"
        headers = {"Authorization": f"Bearer {acc['access_token']}"}
        payload = {"messaging_product": "whatsapp", "to": body.to, "type": "text", "text": {"body": body.text}}
        r = requests.post(f"{base}/{acc['phone_number_id']}/messages", headers=headers, json=payload, timeout=15)
        return r.status_code, r.text

    try:
        code, text = await asyncio.to_thread(_send)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Errore di rete: {e}")
    if code != 200:
        raise HTTPException(status_code=400, detail={"message": _wa_error_hint(code, text), "code": code, "body": text[:500]})
    return {"status": "sent", "response": json.loads(text)}

@api.delete("/integrations/whatsapp/{account_id}")
async def whatsapp_delete(account_id: str, user: dict = Depends(get_current_user)):
    require_privileged(user)
    await db.integrations.delete_one({"id": account_id, "company_id": user["company_id"], "type": "whatsapp"})
    return {"ok": True}

# ---- WhatsApp webhook (public) — verify handshake + inbound messages ------
@api.get("/webhooks/whatsapp")
async def whatsapp_webhook_verify(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    acc = await db.integrations.find_one({"type": "whatsapp", "verify_token": token})
    if mode == "subscribe" and acc and challenge:
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")

def _wa_download_media(media_id: str, token: str):
    """Fetch a WhatsApp media file: resolve URL then download bytes. Returns (bytes, mime)."""
    base = f"https://graph.facebook.com/{GRAPH_VERSION}"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{base}/{media_id}", headers=headers, timeout=15)
    r.raise_for_status()
    info = r.json()
    url, mime = info.get("url"), info.get("mime_type", "")
    rf = requests.get(url, headers=headers, timeout=30)
    rf.raise_for_status()
    return rf.content, mime

async def _wa_source_from_message(msg: dict, acc: dict):
    """Turn a single inbound WhatsApp message into (source_text, image_b64, preview)."""
    sender = msg.get("from")
    mtype = msg.get("type")
    if mtype == "text":
        body = (msg.get("text") or {}).get("body", "")
        return (body, None, f"[WhatsApp da {sender}]\n{body}") if body else (None, None, None)
    if mtype in ("image", "document"):
        media = msg.get(mtype, {})
        media_id = media.get("id")
        if not media_id:
            return None, None, None
        try:
            content, mime = await asyncio.to_thread(_wa_download_media, media_id, acc["access_token"])
        except Exception as e:
            logger.warning("WhatsApp media download failed: %s", e)
            return None, None, None
        fname = (media.get("filename") or "").lower()
        caption = media.get("caption", "")
        if mtype == "image" or mime.startswith("image/"):
            return None, base64.b64encode(content).decode("utf-8"), f"[WhatsApp immagine da {sender}] {caption}"
        if fname.endswith((".csv", ".xlsx", ".xls")) or "spreadsheet" in mime or "excel" in mime or "csv" in mime:
            try:
                df = _read_tabular(content, fname or "f.xlsx")
                return df.to_csv(index=False), None, f"[WhatsApp allegato {fname} da {sender}]"
            except Exception as e:
                logger.warning("WhatsApp tabular parse failed: %s", e); return None, None, None
        if fname.endswith(".pdf") or "pdf" in mime:
            txt = _extract_pdf_text(content)
            if txt.strip():
                return txt, None, f"[WhatsApp PDF {fname} da {sender}]"
        return None, None, None
    return None, None, None

@api.post("/webhooks/whatsapp")
async def whatsapp_webhook_receive(request: Request):
    payload = await request.json()
    created = 0
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                pnid = value.get("metadata", {}).get("phone_number_id")
                acc = await db.integrations.find_one({"type": "whatsapp", "phone_number_id": pnid}, {"_id": 0})
                if not acc:
                    continue
                for msg in value.get("messages", []):
                    try:
                        source_text, image_b64, preview = await _wa_source_from_message(msg, acc)
                        if not source_text and not image_b64:
                            continue
                        order = await ingest_order(
                            acc["company_id"], "whatsapp", preview,
                            source_text=source_text, image_b64=image_b64, created_by="whatsapp",
                            external_id=f"wa:{msg.get('id')}",
                            source_meta={"from": msg.get("from"), "type": msg.get("type")})
                        if order:
                            created += 1
                    except Exception as e:
                        logger.warning("WhatsApp message processing error: %s", e)
    except Exception as e:
        logger.warning("WhatsApp webhook error: %s", e)
    return {"status": "ok", "orders_created": created}

# ---- Email channel --------------------------------------------------------
@api.get("/integrations/email")
async def email_get(user: dict = Depends(get_current_user)):
    doc = await _get_integration(user["company_id"], "email")
    forwarding = f"orders-{user['company_id'][:8]}@inbound.ordia.eu"
    if not doc:
        return {"status": "not_configured", "forwarding_address": forwarding}
    doc.pop("inbound_password", None)
    doc.pop("outbound_password", None)
    doc["forwarding_address"] = forwarding
    return doc

@api.post("/integrations/email")
async def email_save(body: EmailConnect, user: dict = Depends(get_current_user)):
    require_privileged(user)
    cfg = body.model_dump()
    cfg.update({"company_id": user["company_id"], "type": "email", "status": "pending",
                "last_error": None, "updated_at": now_iso()})
    existing = await _get_integration(user["company_id"], "email")
    if existing:
        await db.integrations.update_one({"id": existing["id"]}, {"$set": cfg})
    else:
        cfg["id"] = str(uuid.uuid4())
        cfg["created_at"] = now_iso()
        await db.integrations.insert_one(dict(cfg))
    return {"status": "saved"}

@api.post("/integrations/email/validate")
async def email_validate(user: dict = Depends(get_current_user)):
    require_privileged(user)
    doc = await _get_integration(user["company_id"], "email")
    if not doc:
        raise HTTPException(status_code=400, detail="Configura prima l'email")
    provider = doc.get("inbound_provider")
    if provider == "forwarding":
        await db.integrations.update_one({"id": doc["id"]}, {"$set": {"status": "connected", "last_checked": now_iso()}})
        return {"status": "connected", "mode": "forwarding"}

    def _check():
        results = {}
        host = doc.get("inbound_host") or IMAP_HOSTS.get(provider)
        if host and doc.get("inbound_email") and doc.get("inbound_password"):
            m = imaplib.IMAP4_SSL(host, 993)
            m.login(doc["inbound_email"], doc["inbound_password"])
            m.logout()
            results["inbound"] = "ok"
        if doc.get("outbound_enabled") and doc.get("outbound_host") and doc.get("outbound_email"):
            s = smtplib.SMTP(doc["outbound_host"], int(doc.get("outbound_port") or 587), timeout=15)
            s.starttls()
            s.login(doc["outbound_email"], doc["outbound_password"])
            s.quit()
            results["outbound"] = "ok"
        return results

    try:
        results = await asyncio.to_thread(_check)
    except Exception as e:
        await db.integrations.update_one({"id": doc["id"]}, {"$set": {"status": "error", "last_error": str(e), "last_checked": now_iso()}})
        raise HTTPException(status_code=400, detail=f"Autenticazione email fallita: {e}. Usa una App Password se hai la verifica in due passaggi.")
    await db.integrations.update_one({"id": doc["id"]}, {"$set": {"status": "connected", "last_error": None, "last_checked": now_iso()}})
    return {"status": "connected", "checks": results}

# ---- Real inbound email polling (IMAP) ------------------------------------
def _decode_hdr(value: str) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = ""
    for txt, enc in parts:
        out += txt.decode(enc or "utf-8", errors="ignore") if isinstance(txt, bytes) else txt
    return out

def _parse_email_sources(raw: bytes):
    """Return (source_text, image_b64, subject, sender, message_id) from a raw RFC822 email."""
    msg = email_lib.message_from_bytes(raw)
    subject = _decode_hdr(msg.get("Subject", ""))
    sender = _decode_hdr(msg.get("From", ""))
    message_id = msg.get("Message-ID", "") or f"{sender}:{subject}"
    body_text, attach_text, image_b64 = "", "", None
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        filename = part.get_filename()
        ctype = part.get_content_type()
        if filename:
            fname = _decode_hdr(filename).lower()
            try:
                content = part.get_payload(decode=True) or b""
            except Exception:
                continue
            if fname.endswith((".csv", ".xlsx", ".xls")):
                try:
                    attach_text += "\n" + _read_tabular(content, fname).to_csv(index=False)
                except Exception as e:
                    logger.warning("email tabular parse failed: %s", e)
            elif fname.endswith(".pdf"):
                try:
                    attach_text += "\n" + _extract_pdf_text(content)
                except Exception as e:
                    logger.warning("email pdf parse failed: %s", e)
            elif fname.endswith((".png", ".jpg", ".jpeg", ".webp")) and not image_b64:
                image_b64 = base64.b64encode(content).decode("utf-8")
        elif ctype == "text/plain":
            try:
                body_text += (part.get_payload(decode=True) or b"").decode(part.get_content_charset() or "utf-8", errors="ignore")
            except Exception:
                pass
    source_text = (body_text + "\n" + attach_text).strip()
    return (source_text or None), (None if source_text else image_b64), subject, sender, message_id

async def poll_email_account(doc: dict, limit: int = 20) -> int:
    """Fetch UNSEEN emails for one connected account and ingest them as orders. Idempotent."""
    provider = doc.get("inbound_provider")
    if provider in (None, "forwarding"):
        return 0
    host = doc.get("inbound_host") or IMAP_HOSTS.get(provider)
    if not (host and doc.get("inbound_email") and doc.get("inbound_password")):
        return 0

    def _fetch():
        out = []
        m = imaplib.IMAP4_SSL(host, 993)
        try:
            m.login(doc["inbound_email"], doc["inbound_password"])
            m.select("INBOX")
            typ, data = m.search(None, "UNSEEN")
            if typ != "OK":
                return out
            ids = data[0].split()[:limit]
            for i in ids:
                typ, msg_data = m.fetch(i, "(RFC822)")
                if typ == "OK" and msg_data and msg_data[0]:
                    out.append(msg_data[0][1])
                    m.store(i, "+FLAGS", "\\Seen")
        finally:
            try:
                m.logout()
            except Exception:
                pass
        return out

    try:
        raws = await asyncio.wait_for(asyncio.to_thread(_fetch), timeout=45)
    except Exception as e:
        logger.warning("IMAP poll failed for company=%s: %s", doc.get("company_id"), e)
        await db.integrations.update_one({"id": doc["id"]}, {"$set": {"last_error": str(e)[:300], "last_checked": now_iso()}})
        return 0

    created = 0
    for raw in raws:
        try:
            source_text, image_b64, subject, sender, mid = _parse_email_sources(raw)
            if not source_text and not image_b64:
                continue
            preview = f"[Email da {sender}] {subject}\n{(source_text or '')[:1500]}"
            order = await ingest_order(
                doc["company_id"], "email", preview, source_text=source_text, image_b64=image_b64,
                created_by="email", external_id=f"mail:{mid}",
                source_meta={"from": sender, "subject": subject})
            if order:
                created += 1
        except Exception as e:
            logger.warning("email ingest error: %s", e)
    await db.integrations.update_one({"id": doc["id"]}, {"$set": {"last_checked": now_iso(), "last_error": None}})
    if created:
        logger.info("Email poll ingested %d orders for company=%s", created, doc.get("company_id"))
    return created

@api.post("/integrations/email/poll")
async def email_poll_now(user: dict = Depends(get_current_user)):
    require_privileged(user)
    doc = await _get_integration(user["company_id"], "email")
    if not doc or doc.get("status") != "connected":
        raise HTTPException(status_code=400, detail="Connetti e verifica prima la casella email.")
    created = await poll_email_account(doc)
    return {"status": "ok", "orders_created": created}

async def email_poll_loop():
    """Background loop that polls all connected IMAP mailboxes on an interval."""
    interval = int(os.environ.get("EMAIL_POLL_INTERVAL", "120"))
    await asyncio.sleep(15)  # let startup settle
    while True:
        try:
            accounts = await db.integrations.find(
                {"type": "email", "status": "connected"}, {"_id": 0}).to_list(1000)
            for acc in accounts:
                if acc.get("inbound_provider") not in (None, "forwarding"):
                    await poll_email_account(acc)
        except Exception as e:
            logger.warning("email_poll_loop cycle error: %s", e)
        await asyncio.sleep(interval)

# ---- ERP export layer (provider-based, ERP-agnostic) ----------------------
def standardize_order(order: dict, company: dict) -> dict:
    """Canonical internal export format — the single contract every ERP connector consumes."""
    return {
        "schema": "ordia.order.v1",
        "order_id": order["id"],
        "company": {"id": company.get("id"), "name": company.get("name"), "vat": company.get("vat")},
        "customer": {"name": order.get("customer_name")},
        "delivery_date": order.get("delivery_date"),
        "notes": order.get("notes"),
        "currency": company.get("currency", "EUR"),
        "lines": [
            {"sku": i.get("matched_sku"), "product": i.get("matched_name") or i.get("raw_text"),
             "quantity": i.get("quantity"), "unit": i.get("unit"), "unit_price": i.get("price"),
             "line_total": round((i.get("price") or 0) * (i.get("quantity") or 0), 2)}
            for i in order.get("line_items", [])
        ],
        "total": round(sum((i.get("price") or 0) * (i.get("quantity") or 0) for i in order.get("line_items", [])), 2),
    }

def _standard_to_xml(std: dict) -> str:
    lines = "".join(
        f'<line><sku>{l["sku"] or ""}</sku><product>{l["product"]}</product>'
        f'<quantity>{l["quantity"]}</quantity><unit>{l["unit"]}</unit>'
        f'<unit_price>{l["unit_price"]}</unit_price></line>' for l in std["lines"])
    return (f'<?xml version="1.0" encoding="UTF-8"?><order id="{std["order_id"]}">'
            f'<customer>{std["customer"]["name"] or ""}</customer>'
            f'<total>{std["total"]}</total><lines>{lines}</lines></order>')

@api.get("/integrations/erp")
async def erp_get(user: dict = Depends(get_current_user)):
    doc = await _get_integration(user["company_id"], "erp")
    if not doc:
        return {"status": "not_configured"}
    if doc.get("auth_header_value"):
        doc["auth_header_value"] = mask_secret(doc["auth_header_value"])
    return doc

@api.post("/integrations/erp")
async def erp_save(body: ERPConnect, user: dict = Depends(get_current_user)):
    require_privileged(user)
    cfg = body.model_dump()
    cfg.update({"company_id": user["company_id"], "type": "erp", "status": "pending", "updated_at": now_iso()})
    existing = await _get_integration(user["company_id"], "erp")
    if existing:
        # keep old secret if masked value re-sent
        ahv = cfg.get("auth_header_value") or ""
        if ahv.endswith("…") or "•" in ahv:
            cfg["auth_header_value"] = existing.get("auth_header_value")
        await db.integrations.update_one({"id": existing["id"]}, {"$set": cfg})
    else:
        cfg["id"] = str(uuid.uuid4())
        cfg["created_at"] = now_iso()
        await db.integrations.insert_one(dict(cfg))
    return {"status": "saved"}

@api.post("/integrations/erp/test")
async def erp_test(user: dict = Depends(get_current_user)):
    require_privileged(user)
    doc = await _get_integration(user["company_id"], "erp")
    if not doc or not doc.get("endpoint_url"):
        raise HTTPException(status_code=400, detail="Configura prima l'endpoint ERP")
    company = await db.companies.find_one({"id": user["company_id"]}, {"_id": 0})
    sample = standardize_order({
        "id": "SAMPLE-0001", "customer_name": "Cliente di Prova", "delivery_date": "domani", "notes": "Test",
        "line_items": [{"matched_sku": "PRD-001", "matched_name": "Roma Tomatoes", "quantity": 3, "unit": "case", "price": 18.5}],
    }, company or {})

    def _send():
        headers = {}
        if doc.get("auth_header_name") and doc.get("auth_header_value"):
            headers[doc["auth_header_name"]] = doc["auth_header_value"]
        fmt = doc.get("format", "json")
        if fmt == "json":
            headers["Content-Type"] = "application/json"
            r = requests.request(doc.get("method", "POST"), doc["endpoint_url"], json=sample, headers=headers, timeout=15)
        elif fmt == "xml":
            headers["Content-Type"] = "application/xml"
            r = requests.request(doc.get("method", "POST"), doc["endpoint_url"], data=_standard_to_xml(sample), headers=headers, timeout=15)
        else:  # csv
            headers["Content-Type"] = "text/csv"
            buf = io.StringIO(); pd.DataFrame(sample["lines"]).to_csv(buf, index=False)
            r = requests.request(doc.get("method", "POST"), doc["endpoint_url"], data=buf.getvalue(), headers=headers, timeout=15)
        return r.status_code, r.text[:500]

    try:
        code, text = await asyncio.to_thread(_send)
    except Exception as e:
        await db.integrations.update_one({"id": doc["id"]}, {"$set": {"status": "error", "last_error": str(e), "last_checked": now_iso()}})
        raise HTTPException(status_code=502, detail=f"Impossibile raggiungere l'endpoint: {e}")
    ok = 200 <= code < 300
    await db.integrations.update_one({"id": doc["id"]}, {"$set": {
        "status": "connected" if ok else "error", "last_error": None if ok else f"HTTP {code}", "last_checked": now_iso()}})
    if not ok:
        raise HTTPException(status_code=400, detail=f"L'endpoint ha risposto HTTP {code}: {text}")
    return {"status": "connected", "code": code}

@api.post("/orders/{order_id}/push-erp")
async def push_order_to_erp(order_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_integration(user["company_id"], "erp")
    if not doc or doc.get("status") != "connected":
        raise HTTPException(status_code=400, detail="Nessun ERP connesso. Configuralo in Configurazione → Export ERP.")
    order = await db.orders.find_one({"id": order_id, "company_id": user["company_id"]}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")
    company = await db.companies.find_one({"id": user["company_id"]}, {"_id": 0})
    std = standardize_order(order, company or {})

    def _send():
        headers = {"Content-Type": "application/json"}
        if doc.get("auth_header_name") and doc.get("auth_header_value"):
            headers[doc["auth_header_name"]] = doc["auth_header_value"]
        r = requests.request(doc.get("method", "POST"), doc["endpoint_url"], json=std, headers=headers, timeout=20)
        return r.status_code

    code = await asyncio.to_thread(_send)
    if not (200 <= code < 300):
        raise HTTPException(status_code=400, detail=f"ERP ha risposto HTTP {code}")
    await db.orders.update_one({"id": order_id}, {"$set": {"status": "exported", "updated_at": now_iso()}})
    return {"status": "pushed", "code": code}

# ---------------------------------------------------------------------------
# Pilot demo workspace seeding
# ---------------------------------------------------------------------------
DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "demo@ordia.app")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo123")

DEMO_ORDERS = [
    {
        "customer_name": "Trattoria Sole",
        "delivery_date": "domani",
        "source_type": "text",
        "status": "validated",
        "days_ago": 1,
        "source_preview": "Ciao, sono Maria della Trattoria Sole. Per domani:\n- 3 casse mozzarella\n- 2 sacchi farina 00\n- 5 scatole pomodori pelati\n- 1 cassa coca\nGrazie!",
        "lines": [
            ("DAI-021", "3 casse mozzarella", 3, 0.99),
            ("DRY-010", "2 sacchi farina 00", 2, 0.97),
            ("CND-070", "5 scatole pomodori pelati", 5, 0.95),
            ("BEV-040", "1 cassa coca", 1, 0.98),
        ],
    },
    {
        "customer_name": "Hotel Aurora",
        "delivery_date": "venerdì",
        "source_type": "email",
        "status": "exported",
        "days_ago": 2,
        "source_preview": "Ordine settimanale Hotel Aurora:\n- 4 box petto di pollo\n- 2 casse olio evo\n- 3 vassoi uova\n- 6 casse acqua naturale",
        "lines": [
            ("MEA-030", "4 box petto di pollo", 4, 0.94),
            ("OIL-050", "2 casse olio evo", 2, 0.96),
            ("DAI-023", "3 vassoi uova", 3, 0.99),
            ("BEV-041", "6 casse acqua naturale", 6, 0.97),
        ],
    },
    {
        "customer_name": "Bar Centrale",
        "delivery_date": "lunedì",
        "source_type": "whatsapp",
        "status": "needs_review",
        "days_ago": 0,
        "source_preview": "Buongiorno! Per lunedì: 2 sacchi zucchero, 5 casse latte, un po' di cornetti (vedere quantità) e 3 casse succo arancia.",
        "lines": [
            ("DRY-011", "2 sacchi zucchero", 2, 0.95),
            ("DAI-020", "5 casse latte", 5, 0.97),
            ("BAK-080", "un po' di cornetti", 2, 0.42),
            ("BEV-042", "3 casse succo arancia", 3, 0.9),
        ],
    },
    {
        "customer_name": "Ristorante Da Marco",
        "delivery_date": "mercoledì",
        "source_type": "image",
        "status": "ready",
        "days_ago": 0,
        "source_preview": "[Immagine: ordine_damarco.jpg]",
        "lines": [
            ("MEA-031", "5kg macinato", 5, 0.88),
            ("FRZ-060", "4 casse patatine", 4, 0.93),
            ("PRD-002", "2 casse insalata iceberg", 2, 0.9),
            ("DAI-022", "1 cassa burro", 1, 0.91),
        ],
    },
    {
        "customer_name": "Pizzeria Vesuvio",
        "delivery_date": "giovedì",
        "source_type": "text",
        "status": "validated",
        "days_ago": 3,
        "source_preview": "Ordine Vesuvio: 6 casse mozzarella, 4 scatole pelati, 3 casse olio girasole, 2 sacchi farina.",
        "lines": [
            ("DAI-021", "6 casse mozzarella", 6, 0.99),
            ("CND-070", "4 scatole pelati", 4, 0.95),
            ("OIL-051", "3 casse olio girasole", 3, 0.94),
            ("DRY-010", "2 sacchi farina", 2, 0.96),
        ],
    },
]

async def seed_demo_workspace():
    """Idempotently ensure a demo company, user, catalog and realistic orders exist
    for the pilot experience. Safe to run on every startup."""
    user = await db.users.find_one({"email": DEMO_EMAIL})
    if not user:
        company_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        await db.companies.insert_one({"id": company_id, "name": "Fresh Foods Ingrosso", "created_at": now_iso()})
        await db.users.insert_one({
            "id": user_id, "company_id": company_id, "email": DEMO_EMAIL, "name": "Demo Admin",
            "password_hash": hash_password(DEMO_PASSWORD), "role": "admin", "created_at": now_iso(),
        })
        user = {"id": user_id, "company_id": company_id}
    company_id = user["company_id"]
    user_id = user["id"]

    if await db.products.count_documents({"company_id": company_id}) == 0:
        await seed_company_catalog(company_id)

    if await db.orders.count_documents({"company_id": company_id, "demo_seed": True}) > 0:
        return

    products = await db.products.find({"company_id": company_id}, {"_id": 0}).to_list(2000)
    by_sku = {p["sku"]: p for p in products}

    for spec in DEMO_ORDERS:
        line_items = []
        for sku, raw, qty, conf in spec["lines"]:
            p = by_sku.get(sku)
            if not p:
                continue
            line_items.append({
                "id": str(uuid.uuid4()), "raw_text": raw, "quantity": float(qty),
                "unit": p["unit"], "matched_product_id": p["id"], "matched_sku": p["sku"],
                "matched_name": p["name"], "price": p["price"], "confidence": conf,
                "needs_review": conf < 0.8,
            })
        ts = (datetime.now(timezone.utc) - timedelta(days=spec["days_ago"], hours=2)).isoformat()
        await db.orders.insert_one({
            "id": str(uuid.uuid4()), "company_id": company_id, "created_by": user_id,
            "source_type": spec["source_type"], "source_preview": spec["source_preview"],
            "customer_name": spec["customer_name"], "delivery_date": spec["delivery_date"],
            "notes": None, "line_items": line_items, "status": spec["status"],
            "demo_seed": True, "created_at": ts, "updated_at": ts,
        })
    logger.info("Demo workspace seeded (%d orders).", len(DEMO_ORDERS))

# ---------------------------------------------------------------------------
# App wiring
# ---------------------------------------------------------------------------
app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.products.create_index("company_id")
    await db.orders.create_index("company_id")
    await db.orders.create_index([("company_id", 1), ("external_id", 1)])
    await db.login_attempts.create_index("identifier")
    await db.integrations.create_index([("company_id", 1), ("type", 1)])
    await db.learned_aliases.create_index([("company_id", 1), ("phrase", 1)], unique=True)
    await seed_demo_workspace()
    asyncio.create_task(email_poll_loop())
    logger.info("Ordia API ready.")

@app.on_event("shutdown")
async def shutdown():
    client.close()
