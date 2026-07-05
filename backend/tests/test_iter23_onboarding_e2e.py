"""
Iteration 23 — Full E2E onboarding test (self-service, brand-new account)

Flow:
  1. Register a brand-new company + user
  2. GET /onboarding/status → 5 steps, 0 done, dismissed=false, all_done=false
  3. PUT /company (profile) → profile.done=true
  4. Trigger a catalog import via POST /products/import-ai/confirm mode='add'
     with 3 new products → catalog.done=true (via db.catalog_imports)
  5. Simulate Bridge: create agent, POST /bridge/pair (NO auth) with pairing_code
     → bridge.done=true and paired agent visible in GET /bridge/agents
  6. Skip whatsapp via POST /onboarding/skip-step {step:'whatsapp'}
  7. Try to skip a REQUIRED step 'catalog' → expect HTTP 400
  8. Create first order via POST /orders/extract (source_type=text) →
     wait for status ∈ {needs_review, validated, exported} → first_order.done=true
  9. Final GET /onboarding/status → required_done=true, all_done=true
 10. POST /onboarding/dismiss → dismissed=true persists across GET
"""
import os
import time
import uuid
import pytest
import requests

# Load /app/frontend/.env
_env_path = "/app/frontend/.env"
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


def _step(status: dict, key: str) -> dict:
    return next((s for s in status.get("steps", []) if s.get("key") == key), {})


@pytest.fixture(scope="module")
def new_account():
    """Register a completely fresh company+user; return an authorized session."""
    ts = int(time.time())
    email = f"e2e+{ts}-{uuid.uuid4().hex[:6]}@example.com"
    payload = {
        "company_name": f"TEST_E2E_Co_{ts}",
        "name": "E2E Test Owner",
        "email": email,
        "password": "e2etestpass123",
    }
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=30)
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text[:400]}"
    body = r.json()
    tok = body.get("access_token")
    assert tok, f"No access_token: {body}"
    s.headers.update({"Authorization": f"Bearer {tok}"})
    user = body["user"]
    return {"session": s, "email": email, "user": user, "company_id": user["company_id"]}


class TestE2EOnboarding:
    """Executed in-order because each step depends on previous state."""

    def test_01_initial_status_5_steps_all_pending(self, new_account):
        s = new_account["session"]
        r = s.get(f"{BASE_URL}/api/onboarding/status", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        steps = body.get("steps", [])
        keys = [x["key"] for x in steps]
        assert keys == ["profile", "catalog", "whatsapp", "bridge", "first_order"], keys
        # All start not-done (profile might be pending because sector/erp_name missing)
        assert not any(x["done"] for x in steps), f"Steps unexpectedly done: {steps}"
        assert body.get("dismissed") is False
        assert body.get("all_done") is False
        assert body.get("required_done") is False
        # Optional flags
        assert _step(body, "profile")["skippable"] is False
        assert _step(body, "catalog")["skippable"] is False
        assert _step(body, "first_order")["skippable"] is False
        assert _step(body, "whatsapp")["skippable"] is True
        assert _step(body, "bridge")["skippable"] is True

    def test_02_skip_required_step_returns_400(self, new_account):
        s = new_account["session"]
        r = s.post(f"{BASE_URL}/api/onboarding/skip-step",
                   json={"step": "catalog"}, timeout=15)
        assert r.status_code == 400, f"Expected 400 for required step skip, got {r.status_code}: {r.text[:300]}"

    def test_03_profile_update_marks_profile_done(self, new_account):
        s = new_account["session"]
        r = s.put(f"{BASE_URL}/api/company", json={
            "name": "TEST_E2E_Renamed",
            "sector": "Alimentari / Food & Beverage",
            "erp_name": "Danea",
        }, timeout=15)
        assert r.status_code == 200, r.text
        # Verify onboarding reflects it
        status = s.get(f"{BASE_URL}/api/onboarding/status", timeout=15).json()
        assert _step(status, "profile")["done"] is True, status
        assert status["required_done"] is False  # catalog + first_order still pending

    def test_04_catalog_import_marks_catalog_done(self, new_account):
        s = new_account["session"]
        ts = int(time.time())
        products = [
            {"name": f"TEST_E2E_prod_A_{ts}", "sku": f"TSA-{ts}", "unit": "kg", "price": 6.50},
            {"name": f"TEST_E2E_prod_B_{ts}", "sku": f"TSB-{ts}", "unit": "kg", "price": 22.90},
            {"name": f"TEST_E2E_prod_C_{ts}", "sku": f"TSC-{ts}", "unit": "L",  "price": 9.90},
        ]
        r = s.post(f"{BASE_URL}/api/products/import-ai/confirm",
                   json={"products": products, "mode": "add"}, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("inserted", 0) >= 1, f"No products inserted: {body}"
        # Onboarding catalog step should now flip
        status = s.get(f"{BASE_URL}/api/onboarding/status", timeout=15).json()
        assert _step(status, "catalog")["done"] is True, status

    def test_05_bridge_simulated_pairing_marks_bridge_done(self, new_account):
        s = new_account["session"]
        r = s.post(f"{BASE_URL}/api/bridge/agents",
                   json={"name": "TEST_E2E_agent"}, timeout=15)
        assert r.status_code == 200, r.text
        agent = r.json()
        code = agent.get("pairing_code")
        assert code and str(code).isdigit(), f"No pairing_code: {agent}"

        # Simulate the desktop agent — POST /bridge/pair with NO auth header
        unauth = requests.Session()
        unauth.headers.update({"Content-Type": "application/json"})
        r2 = unauth.post(f"{BASE_URL}/api/bridge/pair",
                         json={"pairing_code": code}, timeout=15)
        assert r2.status_code == 200, f"Pair failed: {r2.status_code} {r2.text[:300]}"
        pair_body = r2.json()
        assert pair_body.get("token"), f"No token: {pair_body}"
        assert pair_body.get("agent_id") == agent["id"]

        # Onboarding bridge step should now flip
        status = s.get(f"{BASE_URL}/api/onboarding/status", timeout=15).json()
        assert _step(status, "bridge")["done"] is True, status

    def test_06_skip_whatsapp_marks_skipped(self, new_account):
        s = new_account["session"]
        r = s.post(f"{BASE_URL}/api/onboarding/skip-step",
                   json={"step": "whatsapp"}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        wa = _step(body, "whatsapp")
        assert wa.get("skipped") is True, f"whatsapp not skipped: {wa}"

    def test_07_first_order_marks_first_order_done(self, new_account):
        """Create a real order via /orders/extract with a realistic Italian text.
        Poll until AI finishes (status ∈ needs_review/validated/exported)."""
        s = new_account["session"]
        text_order = (
            "Buongiorno, per il ristorante Da Mario: "
            "10 kg mozzarella, 5 casse passata di pomodoro, "
            "3 kg parmigiano. Consegna giovedì."
        )
        # FastAPI Form(...) accepts multipart OR urlencoded — use data= without Content-Type json header
        headers = {k: v for k, v in s.headers.items() if k.lower() != "content-type"}
        r = requests.post(
            f"{BASE_URL}/api/orders/extract",
            data={"source_type": "text", "text": text_order},
            headers=headers,
            timeout=90,
        )
        assert r.status_code == 200, f"extract: {r.status_code} {r.text[:400]}"
        order = r.json()
        order_id = order.get("id")
        assert order_id, f"No order id: {order}"

        # Poll for terminal-ish status
        deadline = time.time() + 60
        final_status = None
        while time.time() < deadline:
            rr = s.get(f"{BASE_URL}/api/orders/{order_id}", timeout=15)
            if rr.status_code == 200:
                final_status = rr.json().get("status")
                if final_status in ("needs_review", "validated", "exported"):
                    break
                if final_status == "error":
                    pytest.fail(f"Order errored: {rr.json()}")
            time.sleep(3)
        assert final_status in ("needs_review", "validated", "exported"), \
            f"Order didn't reach final state (last={final_status})"

        # Onboarding first_order step now done
        status = s.get(f"{BASE_URL}/api/onboarding/status", timeout=15).json()
        assert _step(status, "first_order")["done"] is True, status

    def test_08_all_required_done_and_all_done(self, new_account):
        s = new_account["session"]
        status = s.get(f"{BASE_URL}/api/onboarding/status", timeout=15).json()
        assert status["required_done"] is True, status
        assert status["all_done"] is True, status

    def test_09_dismiss_persists(self, new_account):
        s = new_account["session"]
        r = s.post(f"{BASE_URL}/api/onboarding/dismiss", timeout=15)
        assert r.status_code == 200, r.text
        # reload
        status = s.get(f"{BASE_URL}/api/onboarding/status", timeout=15).json()
        assert status["dismissed"] is True, status
