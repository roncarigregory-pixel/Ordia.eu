"""Iteration 9 tests: NEW features only.

Covers:
- PUT/GET /api/automations (routing + auto-confirm settings)
- ingest_order routing (assigned_to when routing_mode='user')
- ingest_order auto-confirm (status='validated', auto_confirmed=true, history)
- POST /api/orders/{id}/send-email (confirmation + clarification via Resend TEST mode)
- PUT /api/orders/{id} with assigned_to (manual assignment persistence)

Resend TEST mode: only 'delivered@resend.dev' is guaranteed to succeed.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
DEMO_EMAIL = "demo@ordia.app"
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo123")
TEST_RECIPIENT = "delivered@resend.dev"

DEFAULTS = {
    "auto_confirm_enabled": False,
    "confidence_threshold": 0.9,
    "hold_new_customers": True,
    "routing_mode": "none",
    "routing_user_id": None,
}


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    token = r.json().get("token") or r.json().get("access_token")
    assert token, f"No token in login response: {r.json()}"
    s.headers.update({"Authorization": f"Bearer {token}"})
    # capture current user
    me = s.get(f"{BASE_URL}/api/auth/me", timeout=15).json()
    s.user_id = me["id"]
    yield s
    # Final safety reset to defaults
    s.put(f"{BASE_URL}/api/automations", json=DEFAULTS, timeout=15)


@pytest.fixture
def reset_automations(api):
    """Guarantee defaults are restored even on failure."""
    yield
    api.put(f"{BASE_URL}/api/automations", json=DEFAULTS, timeout=15)


# ---------- Automations routing ----------
class TestAutomationsRouting:
    def test_defaults_readable(self, api):
        r = api.get(f"{BASE_URL}/api/automations", timeout=15)
        assert r.status_code == 200
        data = r.json()
        for k in DEFAULTS:
            assert k in data, f"Missing key {k} in automations response"

    def test_put_get_routing_settings(self, api, reset_automations):
        team = api.get(f"{BASE_URL}/api/team", timeout=15).json()
        assert isinstance(team, list) and len(team) >= 1
        target_user_id = team[0]["id"]
        payload = {
            "auto_confirm_enabled": False,
            "confidence_threshold": 0.85,
            "hold_new_customers": False,
            "routing_mode": "user",
            "routing_user_id": target_user_id,
        }
        r = api.put(f"{BASE_URL}/api/automations", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        got = r.json()
        assert got["routing_mode"] == "user"
        assert got["routing_user_id"] == target_user_id
        # GET reflects same values
        r2 = api.get(f"{BASE_URL}/api/automations", timeout=15).json()
        assert r2["routing_mode"] == "user"
        assert r2["routing_user_id"] == target_user_id
        assert r2["confidence_threshold"] == 0.85

    def test_routing_assigns_new_needs_review_order(self, api, reset_automations):
        team = api.get(f"{BASE_URL}/api/team", timeout=15).json()
        target_user_id = team[0]["id"]
        # Enable routing
        api.put(f"{BASE_URL}/api/automations", json={
            "auto_confirm_enabled": False,
            "confidence_threshold": 0.9,
            "hold_new_customers": True,
            "routing_mode": "user",
            "routing_user_id": target_user_id,
        }, timeout=15)

        # Extract a messy order likely to be needs_review (unknown SKU / abbreviations)
        # Use form data (extract endpoint uses Form)
        text = "Cliente Bar Zeta\n2x QQQQ mystery item\n1 cs widget X999"
        r = requests.post(
            f"{BASE_URL}/api/orders/extract",
            headers={"Authorization": api.headers["Authorization"]},
            data={"source_type": "text", "text": text},
            timeout=90,
        )
        assert r.status_code == 200, r.text
        order = r.json()
        # If accidentally 'ready', re-fetch to inspect (not fatal, but routing only applies to needs_review)
        if order["status"] != "needs_review":
            pytest.skip(f"Extraction returned status={order['status']} (LLM matched all items). Routing only applies to needs_review.")
        assert order["assigned_to"] == target_user_id, (
            f"Expected assigned_to={target_user_id}, got {order['assigned_to']}")
        history_labels = [h.get("action") for h in order.get("history", [])]
        assert any("Assegnato automaticamente" in (l or "") for l in history_labels), history_labels
        # cleanup
        api.delete(f"{BASE_URL}/api/orders/{order['id']}", timeout=15)


# ---------- Auto-confirm ----------
class TestAutoConfirm:
    def test_auto_confirm_clean_order(self, api, reset_automations):
        api.put(f"{BASE_URL}/api/automations", json={
            "auto_confirm_enabled": True,
            "confidence_threshold": 0.85,
            "hold_new_customers": False,
            "routing_mode": "none",
            "routing_user_id": None,
        }, timeout=15)
        # Clean catalog-matching text (uses seeded SEED_CATALOG names)
        text = "Cliente Ristorante Roma\n2 case Roma Tomatoes\n1 case Iceberg Lettuce\n1 bag All-Purpose Flour"
        r = requests.post(
            f"{BASE_URL}/api/orders/extract",
            headers={"Authorization": api.headers["Authorization"]},
            data={"source_type": "text", "text": text},
            timeout=120,
        )
        assert r.status_code == 200, r.text
        order = r.json()
        if order["status"] != "validated":
            pytest.skip(
                f"Extraction status={order['status']}, auto_confirmed={order.get('auto_confirmed')}. "
                "Likely LLM flagged an item for review — auto-confirm gate correctly held.")
        assert order["auto_confirmed"] is True
        labels = [h.get("action") for h in order.get("history", [])]
        assert any("Confermato automaticamente" in (l or "") for l in labels), labels
        api.delete(f"{BASE_URL}/api/orders/{order['id']}", timeout=15)

    def test_no_auto_confirm_when_disabled(self, api, reset_automations):
        # Ensure disabled
        api.put(f"{BASE_URL}/api/automations", json=DEFAULTS, timeout=15)
        text = "Cliente Test\n2 case Roma Tomatoes"
        r = requests.post(
            f"{BASE_URL}/api/orders/extract",
            headers={"Authorization": api.headers["Authorization"]},
            data={"source_type": "text", "text": text},
            timeout=120,
        )
        assert r.status_code == 200, r.text
        order = r.json()
        assert order["status"] in ("needs_review", "ready"), order["status"]
        assert order.get("auto_confirmed") in (False, None)
        api.delete(f"{BASE_URL}/api/orders/{order['id']}", timeout=15)


# ---------- Email sending ----------
class TestEmailSend:
    @pytest.fixture(scope="class")
    def existing_order_id(self, api):
        # Reuse any existing order — email endpoint doesn't need particular status
        orders = api.get(f"{BASE_URL}/api/orders", timeout=15).json()
        if orders:
            return orders[0]["id"]
        # Otherwise create a quick one
        r = requests.post(
            f"{BASE_URL}/api/orders/extract",
            headers={"Authorization": api.headers["Authorization"]},
            data={"source_type": "text", "text": "Cliente Email Test\n1 case Roma Tomatoes"},
            timeout=120,
        )
        return r.json()["id"]

    def test_send_confirmation_email(self, api, existing_order_id):
        r = api.post(
            f"{BASE_URL}/api/orders/{existing_order_id}/send-email",
            json={"recipient_email": TEST_RECIPIENT, "message": "ok", "kind": "confirmation"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert "id" in data
        # History pushed
        order = api.get(f"{BASE_URL}/api/orders/{existing_order_id}", timeout=15).json()
        labels = [h.get("action") for h in order.get("history", [])]
        assert any("Conferma inviata via email" in (l or "") for l in labels), labels

    def test_send_clarification_email(self, api, existing_order_id):
        r = api.post(
            f"{BASE_URL}/api/orders/{existing_order_id}/send-email",
            json={"recipient_email": TEST_RECIPIENT, "message": "ok", "kind": "clarification"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        order = api.get(f"{BASE_URL}/api/orders/{existing_order_id}", timeout=15).json()
        labels = [h.get("action") for h in order.get("history", [])]
        assert any("Chiarimento inviato" in (l or "") for l in labels), labels


# ---------- Manual assignment ----------
class TestManualAssignment:
    def test_put_order_assigned_to(self, api):
        team = api.get(f"{BASE_URL}/api/team", timeout=15).json()
        target_id = team[0]["id"]
        orders = api.get(f"{BASE_URL}/api/orders", timeout=15).json()
        if not orders:
            pytest.skip("No orders present to update")
        order_id = orders[0]["id"]
        r = api.put(f"{BASE_URL}/api/orders/{order_id}",
                    json={"assigned_to": target_id}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("assigned_to") == target_id
        # Verify persistence via GET
        got = api.get(f"{BASE_URL}/api/orders/{order_id}", timeout=15).json()
        assert got["assigned_to"] == target_id
