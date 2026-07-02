"""Ordia backend API tests — covers auth, catalog, orders, extraction, dashboard, export."""
import os
import io
import uuid
import base64
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fall back to reading frontend .env
    with open("/app/frontend/.env") as fh:
        for line in fh:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

API = f"{BASE_URL}/api"
DEMO_EMAIL = "demo@ordia.app"
DEMO_PASS = "demo123"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s

@pytest.fixture(scope="module")
def demo_token(session):
    # try demo login; if locked, wait a bit
    for _ in range(2):
        r = session.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASS})
        if r.status_code == 200:
            return r.json()["access_token"]
        if r.status_code == 429:
            time.sleep(2)
    pytest.fail(f"Demo login failed: {r.status_code} {r.text}")

@pytest.fixture(scope="module")
def demo_headers(demo_token):
    return {"Authorization": f"Bearer {demo_token}"}

@pytest.fixture(scope="module")
def new_company(session):
    """Register a brand-new company for isolation tests."""
    unique = uuid.uuid4().hex[:10]
    email = f"test_{unique}@example.com"
    body = {
        "company_name": f"TEST_Co_{unique}",
        "name": "Test User",
        "email": email,
        "password": "testpass123",
    }
    r = session.post(f"{API}/auth/register", json=body)
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
    data = r.json()
    return {
        "token": data["access_token"],
        "user": data["user"],
        "email": email,
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }


@pytest.fixture(scope="module")
def seeded_order(session, new_company):
    """Create an order via extraction so downstream Orders/Dashboard tests have data
    even when xdist loadscope splits classes across workers (each worker gets its own new_company)."""
    text = "2 case mozzarella\n1 bag flour 25kg\n5 kg chicken breast\n"
    s = requests.Session()
    s.headers.update(new_company["headers"])
    r = s.post(f"{API}/orders/extract", data={"source_type": "text", "text": text}, timeout=90)
    assert r.status_code == 200, f"seed extract failed: {r.status_code} {r.text}"
    return r.json()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class TestAuth:
    def test_register_seeds_catalog(self, session, new_company):
        assert "access_token" in {"access_token": new_company["token"]}
        assert new_company["user"]["email"] == new_company["email"]
        # GET /auth/me
        r = session.get(f"{API}/auth/me", headers=new_company["headers"])
        assert r.status_code == 200
        assert r.json()["email"] == new_company["email"]
        # Products seeded
        r = session.get(f"{API}/products", headers=new_company["headers"])
        assert r.status_code == 200
        products = r.json()
        assert len(products) >= 20, f"Expected seeded catalog, got {len(products)}"
        # No _id leak
        assert all("_id" not in p for p in products)

    def test_login_demo_success(self, session):
        r = session.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASS})
        assert r.status_code == 200, f"Demo login failed: {r.text}"
        data = r.json()
        assert "access_token" in data
        assert data["user"]["email"] == DEMO_EMAIL

    def test_login_wrong_password(self, session):
        r = session.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": "wrong_bad_pw"})
        # after failed attempt, 401 unless previously locked (429)
        assert r.status_code in (401, 429), f"Got {r.status_code}: {r.text}"

    def test_me_requires_token(self, session):
        # Use a bare request (no session cookie/header) — must be unauthenticated.
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_register_duplicate_email_rejected(self, session, new_company):
        r = session.post(f"{API}/auth/register", json={
            "company_name": "dup", "name": "dup",
            "email": new_company["email"], "password": "testpass123",
        })
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Catalog (isolation + CRUD)
# ---------------------------------------------------------------------------
class TestCatalog:
    def test_multi_tenant_isolation(self, session, new_company, demo_headers):
        # Add custom product to new company
        r = session.post(f"{API}/products", headers=new_company["headers"], json={
            "sku": "TEST_ISO_1", "name": "TEST_isolated_widget",
            "category": "Test", "unit": "unit", "price": 1.0, "aliases": ["testiso"],
        })
        assert r.status_code == 200
        created_id = r.json()["id"]
        assert r.json()["sku"] == "TEST_ISO_1"

        # Demo user's list should NOT contain it
        r = session.get(f"{API}/products", headers=demo_headers)
        assert r.status_code == 200
        ids = {p["id"] for p in r.json()}
        assert created_id not in ids, "Multi-tenant leak: demo can see other co's product"

        # Cleanup
        session.delete(f"{API}/products/{created_id}", headers=new_company["headers"])

    def test_product_crud(self, session, new_company):
        h = new_company["headers"]
        # Create
        r = session.post(f"{API}/products", headers=h, json={
            "sku": "TEST_CRUD_1", "name": "TEST_CRUD_Product",
            "category": "Test", "unit": "case", "price": 9.99, "aliases": ["tcrud"],
        })
        assert r.status_code == 200
        pid = r.json()["id"]

        # Update
        r = session.put(f"{API}/products/{pid}", headers=h, json={
            "sku": "TEST_CRUD_1", "name": "TEST_CRUD_Updated",
            "category": "Test", "unit": "case", "price": 12.5, "aliases": ["tcrud"],
        })
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_CRUD_Updated"
        assert r.json()["price"] == 12.5

        # Verify via list
        r = session.get(f"{API}/products", headers=h)
        found = next((p for p in r.json() if p["id"] == pid), None)
        assert found and found["name"] == "TEST_CRUD_Updated"

        # Delete
        r = session.delete(f"{API}/products/{pid}", headers=h)
        assert r.status_code == 200
        r = session.get(f"{API}/products", headers=h)
        assert not any(p["id"] == pid for p in r.json())


# ---------------------------------------------------------------------------
# AI Extraction (core)
# ---------------------------------------------------------------------------
class TestExtraction:
    def _extract_text(self, session, headers, text):
        # multipart form
        s = requests.Session()
        s.headers.update(headers)
        r = s.post(f"{API}/orders/extract", data={"source_type": "text", "text": text}, timeout=90)
        return r

    def test_extract_text_whatsapp(self, session, new_company):
        text = (
            "Ciao, per domani mattina:\n"
            "3 casse mozzarella\n"
            "2 sacchi flour 25kg\n"
            "1 case chopped toms\n"
            "5 kg ckn breast\n"
            "Grazie - Ristorante Mario"
        )
        r = self._extract_text(session, new_company["headers"], text)
        assert r.status_code == 200, f"Extract failed: {r.status_code} {r.text}"
        order = r.json()
        assert "id" in order and "line_items" in order
        items = order["line_items"]
        assert len(items) >= 3, f"Expected >=3 items, got {len(items)}"
        # At least one item should have matched a product
        matched = [i for i in items if i.get("matched_product_id")]
        assert len(matched) >= 1, "No AI match on any line item"
        # Order persisted
        r = session.get(f"{API}/orders/{order['id']}", headers=new_company["headers"])
        assert r.status_code == 200
        # save order id for subsequent tests
        pytest.text_order_id = order["id"]

    def test_extract_csv_file(self, session, new_company):
        csv_data = "product,quantity,unit\nMozzarella,3,case\nFlour 25kg,2,bag\nPenne Pasta,4,case\n"
        s = requests.Session()
        s.headers.update(new_company["headers"])
        files = {"file": ("order.csv", csv_data, "text/csv")}
        data = {"source_type": "file"}
        r = s.post(f"{API}/orders/extract", data=data, files=files, timeout=90)
        assert r.status_code == 200, f"CSV extract failed: {r.status_code} {r.text}"
        order = r.json()
        assert len(order["line_items"]) >= 2

    def test_extract_image_file(self, session, new_company):
        # Generate a real image with text using PIL
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            pytest.skip("PIL not available")
        img = Image.new("RGB", (600, 300), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        # Add real content
        for i, line in enumerate([
            "ORDER - Restaurant Milano",
            "3 case mozzarella",
            "2 bag flour 25kg",
            "5 kg chicken breast",
        ]):
            draw.text((20, 30 + i * 50), line, fill=(0, 0, 0))
        # Add features (rectangles) so it's not a blank image
        draw.rectangle([10, 10, 590, 290], outline=(50, 50, 200), width=3)
        draw.line([(20, 20), (580, 280)], fill=(200, 50, 50), width=2)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        s = requests.Session()
        s.headers.update(new_company["headers"])
        files = {"file": ("order.png", buf.getvalue(), "image/png")}
        data = {"source_type": "file"}
        r = s.post(f"{API}/orders/extract", data=data, files=files, timeout=120)
        assert r.status_code == 200, f"Image extract failed: {r.status_code} {r.text}"
        order = r.json()
        assert "line_items" in order


# ---------------------------------------------------------------------------
# Orders CRUD / validate / export
# ---------------------------------------------------------------------------
class TestOrders:
    def test_list_and_get(self, session, new_company, seeded_order):
        r = session.get(f"{API}/orders", headers=new_company["headers"])
        assert r.status_code == 200
        orders = r.json()
        assert len(orders) >= 1
        # Get single
        r = session.get(f"{API}/orders/{seeded_order['id']}", headers=new_company["headers"])
        assert r.status_code == 200

    def test_update_order(self, session, new_company, seeded_order):
        oid = seeded_order["id"]
        update = {"customer_name": "TEST_Customer", "notes": "TEST_note"}
        r = session.put(f"{API}/orders/{oid}", headers=new_company["headers"], json=update)
        assert r.status_code == 200
        assert r.json()["customer_name"] == "TEST_Customer"
        # Persistence check
        r = session.get(f"{API}/orders/{oid}", headers=new_company["headers"])
        assert r.json()["customer_name"] == "TEST_Customer"

    def test_validate_order(self, session, new_company, seeded_order):
        oid = seeded_order["id"]
        r = session.post(f"{API}/orders/{oid}/validate", headers=new_company["headers"])
        assert r.status_code == 200
        assert r.json()["status"] == "validated"

    def test_export_csv(self, session, new_company, seeded_order):
        oid = seeded_order["id"]
        r = session.get(f"{API}/orders/{oid}/export?format=csv", headers=new_company["headers"])
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        assert "attachment" in r.headers.get("content-disposition", "")
        r2 = session.get(f"{API}/orders/{oid}", headers=new_company["headers"])
        assert r2.json()["status"] == "exported"

    def test_export_json(self, session, new_company, seeded_order):
        oid = seeded_order["id"]
        r = session.get(f"{API}/orders/{oid}/export?format=json", headers=new_company["headers"])
        assert r.status_code == 200
        assert "application/json" in r.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class TestDashboard:
    def test_stats(self, session, new_company, seeded_order):
        r = session.get(f"{API}/dashboard/stats", headers=new_company["headers"])
        assert r.status_code == 200
        d = r.json()
        for key in ["total_orders", "needs_review", "processed", "accuracy", "hours_saved", "products", "recent"]:
            assert key in d, f"Missing stats key: {key}"
        assert d["products"] >= 20
        assert d["total_orders"] >= 1
        assert isinstance(d["recent"], list)
