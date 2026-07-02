"""Ordia P0 lifecycle & Command Center backend tests.
Covers: extract -> get -> update -> validate -> export (4 formats) -> history -> command-center.
"""
import os, io, json, uuid, time
import pytest
import requests

BASE_URL = ""
with open("/app/frontend/.env") as fh:
    for line in fh:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE_URL}/api"

DEMO_EMAIL = "demo@ordia.app"
DEMO_PASS = "demo123"


@pytest.fixture(scope="module")
def demo_headers():
    r = requests.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASS}, timeout=30)
    if r.status_code == 429:
        time.sleep(3)
        r = requests.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASS}, timeout=30)
    assert r.status_code == 200, f"Demo login failed: {r.status_code} {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def new_company():
    unique = uuid.uuid4().hex[:10]
    email = f"test_p0_{unique}@example.com"
    r = requests.post(f"{API}/auth/register", json={
        "company_name": f"TEST_P0_{unique}", "name": "P0 Tester",
        "email": email, "password": "testpass123"}, timeout=30)
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
    tok = r.json()["access_token"]
    return {"headers": {"Authorization": f"Bearer {tok}"}, "email": email}


@pytest.fixture(scope="module")
def extracted_order(new_company):
    """Full text extraction via Claude — allow up to 60s."""
    text = ("Ordine per venerdì:\n"
            "3 casse mozzarella\n"
            "2 sacchi farina 25kg\n"
            "5 kg petto di pollo\n"
            "Ristorante Da Luca")
    r = requests.post(f"{API}/orders/extract",
                      data={"source_type": "text", "text": text},
                      headers=new_company["headers"], timeout=90)
    assert r.status_code == 200, f"Extract failed: {r.status_code} {r.text}"
    return r.json()


# ---------- Extraction & Get ----------
class TestExtractAndGet:
    def test_extract_creates_order(self, extracted_order):
        assert "id" in extracted_order
        assert "line_items" in extracted_order
        assert len(extracted_order["line_items"]) >= 2
        assert extracted_order["source_type"] == "text"
        # No _id leak
        assert "_id" not in extracted_order

    def test_extract_has_history_entry(self, extracted_order):
        hist = extracted_order.get("history", [])
        assert len(hist) >= 1
        assert any("estratto" in (h.get("action", "") + h.get("detail", "")).lower() for h in hist)

    def test_get_order(self, new_company, extracted_order):
        oid = extracted_order["id"]
        r = requests.get(f"{API}/orders/{oid}", headers=new_company["headers"], timeout=30)
        assert r.status_code == 200
        assert r.json()["id"] == oid
        assert "_id" not in r.json()

    def test_get_order_not_found(self, new_company):
        r = requests.get(f"{API}/orders/nonexistent-xyz", headers=new_company["headers"], timeout=30)
        assert r.status_code == 404


# ---------- Update (persist edits) ----------
class TestUpdate:
    def test_update_customer_and_delivery(self, new_company, extracted_order):
        oid = extracted_order["id"]
        upd = {"customer_name": "TEST_Cliente_P0", "delivery_date": "2026-01-15",
               "notes": "TEST note"}
        r = requests.put(f"{API}/orders/{oid}", json=upd, headers=new_company["headers"], timeout=30)
        assert r.status_code == 200
        j = r.json()
        assert j["customer_name"] == "TEST_Cliente_P0"
        assert j["delivery_date"] == "2026-01-15"
        # GET verify
        r2 = requests.get(f"{API}/orders/{oid}", headers=new_company["headers"], timeout=30)
        assert r2.json()["customer_name"] == "TEST_Cliente_P0"
        assert r2.json()["notes"] == "TEST note"

    def test_update_pushes_history(self, new_company, extracted_order):
        oid = extracted_order["id"]
        r = requests.get(f"{API}/orders/{oid}", headers=new_company["headers"], timeout=30)
        hist = r.json().get("history", [])
        assert any("Modifiche salvate" in h.get("action", "") for h in hist), \
            f"History missing 'Modifiche salvate': {hist}"


# ---------- Validate ----------
class TestValidate:
    def test_validate_sets_status(self, new_company, extracted_order):
        oid = extracted_order["id"]
        r = requests.post(f"{API}/orders/{oid}/validate", headers=new_company["headers"], timeout=30)
        assert r.status_code == 200
        assert r.json()["status"] == "validated"
        # GET verify + history entry
        r2 = requests.get(f"{API}/orders/{oid}", headers=new_company["headers"], timeout=30)
        assert r2.json()["status"] == "validated"
        hist = r2.json().get("history", [])
        assert any("confermato" in h.get("action", "").lower() for h in hist), \
            f"History missing confirm entry: {hist}"


# ---------- Export (4 formats) ----------
class TestExport:
    def _ext(self, headers, oid, fmt):
        return requests.get(f"{API}/orders/{oid}/export?format={fmt}", headers=headers, timeout=60)

    def test_export_csv(self, new_company, extracted_order):
        r = self._ext(new_company["headers"], extracted_order["id"], "csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        assert "attachment" in r.headers.get("content-disposition", "").lower()
        assert ".csv" in r.headers.get("content-disposition", "")
        assert len(r.content) > 20

    def test_export_json(self, new_company, extracted_order):
        r = self._ext(new_company["headers"], extracted_order["id"], "json")
        assert r.status_code == 200
        assert "application/json" in r.headers.get("content-type", "")
        assert ".json" in r.headers.get("content-disposition", "")
        payload = json.loads(r.content)
        assert "order_id" in payload
        assert "line_items" in payload
        assert "total" in payload

    def test_export_excel(self, new_company, extracted_order):
        r = self._ext(new_company["headers"], extracted_order["id"], "excel")
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers.get("content-type", "")
        assert ".xlsx" in r.headers.get("content-disposition", "")
        # xlsx = zip, starts with PK
        assert r.content[:2] == b"PK", "Excel content is not a valid xlsx"

    def test_export_pdf(self, new_company, extracted_order):
        r = self._ext(new_company["headers"], extracted_order["id"], "pdf")
        assert r.status_code == 200
        assert "application/pdf" in r.headers.get("content-type", "")
        assert ".pdf" in r.headers.get("content-disposition", "")
        assert r.content[:4] == b"%PDF", "PDF magic bytes missing"

    def test_export_sets_status_and_history(self, new_company, extracted_order):
        oid = extracted_order["id"]
        r = requests.get(f"{API}/orders/{oid}", headers=new_company["headers"], timeout=30)
        j = r.json()
        assert j["status"] == "exported"
        hist = j.get("history", [])
        assert any("Esportato" in h.get("action", "") for h in hist)


# ---------- Command Center ----------
class TestCommandCenter:
    def test_command_center_shape(self, new_company, extracted_order):
        r = requests.get(f"{API}/command-center", headers=new_company["headers"], timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ["today", "to_review", "recent_activity", "notifications", "recent_customers", "totals"]:
            assert k in d, f"missing key {k}"
        assert isinstance(d["today"], dict)
        for tk in ["total", "auto", "review"]:
            assert tk in d["today"]
        assert isinstance(d["to_review"], list)
        assert isinstance(d["recent_activity"], list)
        assert isinstance(d["recent_customers"], list)
        assert d["totals"]["orders"] >= 1

    def test_command_center_recent_customer_populated(self, new_company, extracted_order):
        # order was updated to TEST_Cliente_P0 above
        r = requests.get(f"{API}/command-center", headers=new_company["headers"], timeout=30)
        names = [c["name"] for c in r.json()["recent_customers"]]
        assert any("TEST_Cliente_P0" in n or "sconosciuto" in n.lower() for n in names) or len(names) >= 1

    def test_command_center_no_id_leak(self, new_company):
        r = requests.get(f"{API}/command-center", headers=new_company["headers"], timeout=30)
        blob = json.dumps(r.json())
        # ensure no bson _id leaked
        assert '"_id"' not in blob

    def test_command_center_demo_has_real_data(self, demo_headers):
        r = requests.get(f"{API}/command-center", headers=demo_headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        # Demo tenant should have seeded data
        assert d["totals"]["orders"] >= 1


# ---------- Orders list ----------
class TestOrdersList:
    def test_orders_list_returns(self, new_company, extracted_order):
        r = requests.get(f"{API}/orders", headers=new_company["headers"], timeout=30)
        assert r.status_code == 200
        arr = r.json()
        assert isinstance(arr, list)
        assert len(arr) >= 1
        assert all("_id" not in o for o in arr)


# ---------- Line item edit persistence ----------
class TestLineItemEdit:
    def test_edit_line_item_via_put(self, new_company, extracted_order):
        oid = extracted_order["id"]
        # fetch fresh
        r = requests.get(f"{API}/orders/{oid}", headers=new_company["headers"], timeout=30)
        order = r.json()
        items = order["line_items"]
        assert len(items) >= 1
        # Add a new line item + change qty of first
        items[0]["quantity"] = 99
        items.append({
            "id": uuid.uuid4().hex,
            "raw_text": "TEST added row",
            "quantity": 4,
            "unit": "pz",
            "confidence": 0.99,
        })
        r = requests.put(f"{API}/orders/{oid}",
                         json={"line_items": items},
                         headers=new_company["headers"], timeout=30)
        assert r.status_code == 200
        # verify
        r2 = requests.get(f"{API}/orders/{oid}", headers=new_company["headers"], timeout=30)
        new_items = r2.json()["line_items"]
        assert any(i.get("raw_text") == "TEST added row" for i in new_items)
        first = next((i for i in new_items if i["id"] == items[0]["id"]), None)
        assert first and first["quantity"] == 99
