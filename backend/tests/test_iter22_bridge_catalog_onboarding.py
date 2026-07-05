"""
Iteration 22 — Onboarding P0 tests
- Bridge pairing UX: create agent → code_status/code_expires_at,
  regenerate-code (only when not paired), send-instructions (valid/invalid email)
- Catalog wizard backend: /products/import-ai/text (with _uncertain + _exists),
  /products/template (xlsx), /catalog/status, /products/import-ai/confirm
  (add=skip existing, update=updates existing + inserts new),
  /catalog/import-draft (put/get/delete), /catalog/imports history

Auth: demo@ordia.app / demo123 — bearer token from login response.access_token
"""
import os
import io
import time
import pytest
import requests
from datetime import datetime, timezone

# Load /app/frontend/.env for REACT_APP_BACKEND_URL
_env_path = "/app/frontend/.env"
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
LOGIN = {"email": "demo@ordia.app", "password": "demo123"}

# ---- fixtures ----

@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json=LOGIN, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text[:300]}"
    tok = r.json().get("access_token")
    assert tok, f"No access_token in response: {r.json()}"
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture
def created_agent(session):
    """Create a throwaway bridge agent, delete at teardown."""
    r = session.post(f"{BASE_URL}/api/bridge/agents",
                     json={"name": "TEST_agent_iter22"}, timeout=15)
    assert r.status_code == 200, f"Create agent: {r.status_code} {r.text[:300]}"
    doc = r.json()
    yield doc
    try:
        session.delete(f"{BASE_URL}/api/bridge/agents/{doc['id']}", timeout=10)
    except Exception:
        pass


# ---- Bridge: create agent returns pairing_code + code_status + expiry ----

class TestBridgeAgentCreate:
    def test_create_returns_pairing_code_and_status(self, session):
        r = session.post(f"{BASE_URL}/api/bridge/agents",
                         json={"name": "TEST_agent_create"}, timeout=15)
        assert r.status_code == 200, r.text
        doc = r.json()
        try:
            # Data assertions
            assert doc.get("id"), "Missing id"
            code = doc.get("pairing_code")
            assert isinstance(code, str) and code.isdigit() and len(code) >= 6, \
                f"Bad pairing_code: {code!r}"
            assert doc.get("code_status") == "valid", \
                f"Expected code_status='valid', got {doc.get('code_status')!r}"
            exp = doc.get("code_expires_at")
            assert exp, "Missing code_expires_at"
            # ~7 days in the future (allow 6-8 days)
            expdt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
            delta_days = (expdt - datetime.now(timezone.utc)).total_seconds() / 86400
            assert 6.0 < delta_days < 8.5, f"Expiry not ~7 days ahead: {delta_days:.2f}d"
            assert doc.get("paired") in (False, None)
        finally:
            session.delete(f"{BASE_URL}/api/bridge/agents/{doc['id']}", timeout=10)


# ---- Bridge: regenerate-code returns new code, valid status ----

class TestBridgeRegenerate:
    def test_regenerate_returns_new_code(self, session, created_agent):
        old_code = created_agent["pairing_code"]
        r = session.post(
            f"{BASE_URL}/api/bridge/agents/{created_agent['id']}/regenerate-code",
            timeout=15)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc.get("pairing_code") and doc["pairing_code"] != old_code, \
            f"Code did not change: old={old_code} new={doc.get('pairing_code')}"
        assert doc.get("code_status") == "valid"
        assert doc.get("code_expires_at")


# ---- Bridge: send-instructions ----

class TestBridgeSendInstructions:
    def test_invalid_email_returns_400(self, session, created_agent):
        r = session.post(
            f"{BASE_URL}/api/bridge/agents/{created_agent['id']}/send-instructions",
            json={"email": "not-an-email"}, timeout=15)
        assert r.status_code == 400, f"Expected 400 for invalid email, got {r.status_code}: {r.text[:300]}"

    def test_valid_email_ok_or_config_400(self, session, created_agent):
        r = session.post(
            f"{BASE_URL}/api/bridge/agents/{created_agent['id']}/send-instructions",
            json={"email": "test-recipient@example.com"}, timeout=30)
        # Accept either 200 ok:true OR 400 "Invio email non configurato".
        # Explicitly REJECT 500.
        assert r.status_code != 500, f"500 error: {r.text[:400]}"
        if r.status_code == 200:
            body = r.json()
            assert body.get("ok") is True, f"Expected ok:true, got {body}"
        elif r.status_code == 400:
            body = r.json()
            detail = (body.get("detail") or "").lower()
            # accept both "non configurato" and generic "invio"/config errors
            assert ("configurato" in detail) or ("email" in detail), \
                f"Unexpected 400: {body}"
        elif r.status_code == 502:
            # RESEND accepted the request but failed (network/config).
            # This is not a code bug per se, but a runtime issue — flag as skip.
            pytest.skip(f"Resend 502 (integration): {r.text[:200]}")
        else:
            pytest.fail(f"Unexpected status {r.status_code}: {r.text[:300]}")


# ---- Catalog: /products/import-ai/text ----

SAMPLE_TEXT = """
Mozzarella Fiordilatte 400g 6,50
Passata di Pomodoro 700g 2,20
Parmigiano Reggiano 24 mesi kg  22,90
Olio Extravergine 1L
""".strip()


class TestCatalogImportText:
    def test_import_text_returns_products_with_flags(self, session):
        r = session.post(f"{BASE_URL}/api/products/import-ai/text",
                         json={"text": SAMPLE_TEXT}, timeout=60)
        assert r.status_code == 200, f"import-ai/text: {r.status_code} {r.text[:300]}"
        body = r.json()
        assert body.get("count", 0) > 0, f"No products extracted: {body}"
        products = body["products"]
        assert isinstance(products, list) and len(products) >= 1
        # Each product should have _uncertain (list) and _exists (bool)
        for p in products:
            assert isinstance(p.get("_uncertain"), list), \
                f"Missing _uncertain on {p.get('name')!r}: {p}"
            assert isinstance(p.get("_exists"), bool), \
                f"Missing _exists on {p.get('name')!r}: {p}"
            assert p.get("name"), "Product missing name"


# ---- Catalog: /products/template ----

class TestCatalogTemplate:
    def test_template_returns_xlsx(self, session):
        r = session.get(f"{BASE_URL}/api/products/template", timeout=20)
        assert r.status_code == 200, f"template: {r.status_code} {r.text[:200]}"
        ct = r.headers.get("Content-Type", "")
        # Excel spreadsheet content type
        assert "spreadsheet" in ct or "openxmlformats-officedocument" in ct, \
            f"Bad content-type: {ct}"
        assert len(r.content) > 500, f"Response too small: {len(r.content)} bytes"
        # xlsx files begin with PK zip signature
        assert r.content[:2] == b"PK", "Not a valid xlsx (missing PK signature)"


# ---- Catalog: /catalog/status ----

class TestCatalogStatus:
    def test_status_returns_valid_shape(self, session):
        r = session.get(f"{BASE_URL}/api/catalog/status", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("status") in ("absent", "incomplete", "ready"), \
            f"Bad status: {body}"
        assert isinstance(body.get("total"), int)


# ---- Catalog: import-ai/confirm — add vs update vs skip ----

class TestCatalogConfirm:
    def test_add_inserts_new_then_skips_existing(self, session):
        unique_name = f"TEST_iter22_prod_{int(time.time())}"
        prod = {
            "name": unique_name, "sku": f"TSKU-{int(time.time())}",
            "category": "TEST", "unit": "kg", "pack_size": "1x1kg",
            "price": 9.99, "aliases": ["test-alias"],
        }
        # ADD (should insert)
        r = session.post(f"{BASE_URL}/api/products/import-ai/confirm",
                         json={"products": [prod], "mode": "add"}, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("inserted") == 1, f"Expected inserted=1: {body}"
        assert body.get("skipped") == 0

        # find created product id
        created_id = self._find_id(session, unique_name)
        assert created_id, f"Product {unique_name!r} not found after insert"

        try:
            # ADD again → should skip (no duplicate)
            r2 = session.post(f"{BASE_URL}/api/products/import-ai/confirm",
                              json={"products": [prod], "mode": "add"}, timeout=30)
            assert r2.status_code == 200, r2.text
            body2 = r2.json()
            assert body2.get("inserted") == 0, f"Expected inserted=0 on re-add: {body2}"
            assert body2.get("skipped") == 1, f"Expected skipped=1: {body2}"

            # UPDATE — change price, expect updated=1
            prod_up = dict(prod, price=42.50)
            r3 = session.post(f"{BASE_URL}/api/products/import-ai/confirm",
                              json={"products": [prod_up], "mode": "update"}, timeout=30)
            assert r3.status_code == 200, r3.text
            body3 = r3.json()
            assert body3.get("updated") == 1, f"Expected updated=1: {body3}"
            # Verify persisted change
            gr = session.get(f"{BASE_URL}/api/products", timeout=15)
            items = gr.json() if isinstance(gr.json(), list) else gr.json().get("items", [])
            match = next((p for p in items if p.get("id") == created_id), None)
            assert match and abs(float(match["price"]) - 42.50) < 0.01, \
                f"Price not updated: {match}"
        finally:
            session.delete(f"{BASE_URL}/api/products/{created_id}", timeout=15)

    @staticmethod
    def _find_id(session, name):
        r = session.get(f"{BASE_URL}/api/products", timeout=15)
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", [])
        for p in items:
            if p.get("name") == name:
                return p["id"]
        return None


# ---- Catalog: import-draft put/get/delete ----

class TestCatalogDraft:
    def test_put_get_delete_draft(self, session):
        draft_products = [
            {"name": "TEST_draft_1", "price": 1.23, "sku": "D1"},
            {"name": "TEST_draft_2", "price": 4.56, "sku": "D2"},
        ]
        # PUT
        r = session.put(f"{BASE_URL}/api/catalog/import-draft",
                        json={"products": draft_products, "mode": "add"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True
        assert r.json().get("count") == 2

        # GET
        r2 = session.get(f"{BASE_URL}/api/catalog/import-draft", timeout=15)
        assert r2.status_code == 200
        body = r2.json()
        assert len(body.get("products", [])) == 2, f"Draft not fetched: {body}"
        assert body.get("mode") == "add"

        # DELETE
        r3 = session.delete(f"{BASE_URL}/api/catalog/import-draft", timeout=15)
        assert r3.status_code == 200
        assert r3.json().get("ok") is True

        # GET after delete → empty
        r4 = session.get(f"{BASE_URL}/api/catalog/import-draft", timeout=15)
        assert r4.status_code == 200
        assert r4.json().get("products", []) == []


# ---- Catalog: /catalog/imports history ----

class TestCatalogImportsHistory:
    def test_history_after_confirm(self, session):
        # Trigger a confirm to ensure at least one entry
        unique_name = f"TEST_hist_prod_{int(time.time())}"
        prod = {"name": unique_name, "sku": f"HSKU-{int(time.time())}",
                "unit": "kg", "price": 1.0}
        r = session.post(f"{BASE_URL}/api/products/import-ai/confirm",
                         json={"products": [prod], "mode": "add"}, timeout=30)
        assert r.status_code == 200, r.text
        try:
            r2 = session.get(f"{BASE_URL}/api/catalog/imports", timeout=15)
            assert r2.status_code == 200
            body = r2.json()
            items = body.get("items", [])
            assert isinstance(items, list) and len(items) >= 1, \
                f"Empty history after confirm: {body}"
            latest = items[0]
            # Basic shape assertions
            for k in ("id", "mode", "inserted", "updated", "skipped", "total", "created_at"):
                assert k in latest, f"Missing {k!r} in history entry: {latest}"
        finally:
            # cleanup product
            created_id = TestCatalogConfirm._find_id(session, unique_name)
            if created_id:
                session.delete(f"{BASE_URL}/api/products/{created_id}", timeout=15)
