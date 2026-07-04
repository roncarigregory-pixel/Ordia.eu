"""
Iteration 16 — Production release tests:
 - Auth (login existing, register new)
 - No demo auto-login (no anonymous /app data access)
 - Bridge install UX: create agent (unpaired) => pairing_code, download endpoint => zip
 - Order create via text import (AI extraction) + review update line item
"""
import os
import time
import io
import zipfile
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or \
    __import__("subprocess").check_output(
        "grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d= -f2", shell=True
    ).decode().strip()

API = f"{BASE_URL}/api"

DEMO_EMAIL = "demo@ordia.app"
DEMO_PASSWORD = "demo123"


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def demo_token(client):
    r = client.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert r.status_code == 200, f"demo login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data or "access_token" in data
    return data.get("token") or data.get("access_token")


@pytest.fixture(scope="session")
def demo_headers(demo_token):
    return {"Authorization": f"Bearer {demo_token}", "Content-Type": "application/json"}


# ---------- auth ----------
class TestAuth:
    def test_login_demo(self, client):
        r = client.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
        assert r.status_code == 200
        j = r.json()
        assert (j.get("token") or j.get("access_token"))
        u = j.get("user") or {}
        assert u.get("email") == DEMO_EMAIL

    def test_login_wrong_password(self, client):
        r = client.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": "nope"})
        assert r.status_code in (400, 401, 403)

    def test_register_new_user_and_catalog_seed(self, client):
        ts = int(time.time())
        payload = {
            "company_name": f"TEST_Wholesale_{ts}",
            "name": "TEST QA User",
            "email": f"qa+{ts}@ordia.app",
            "password": "Password123",
        }
        r = client.post(f"{API}/auth/register", json=payload)
        assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
        j = r.json()
        token = j.get("token") or j.get("access_token")
        assert token, "no token returned from register"
        u = j.get("user") or {}
        assert u.get("email") == payload["email"]
        # Verify catalog seeded
        h = {"Authorization": f"Bearer {token}"}
        cr = client.get(f"{API}/products", headers=h)
        assert cr.status_code == 200, f"products fetch failed: {cr.status_code}"
        products = cr.json()
        if isinstance(products, dict):
            products = products.get("items") or products.get("products") or []
        assert len(products) > 0, "catalog was not pre-seeded on register"


# ---------- no demo auto-login: anonymous access blocked ----------
class TestNoDemoAutoLogin:
    """Uses a fresh requests.get (no session cookies) to prove endpoints need auth."""
    def test_me_requires_auth(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code in (401, 403), f"expected auth error, got {r.status_code}"

    def test_orders_requires_auth(self):
        r = requests.get(f"{API}/orders")
        assert r.status_code in (401, 403)

    def test_customers_requires_auth(self):
        r = requests.get(f"{API}/customers")
        assert r.status_code in (401, 403)


# ---------- bridge install UX ----------
class TestBridge:
    def test_create_agent_returns_pairing_code(self, client, demo_headers):
        r = client.post(f"{API}/bridge/agents", headers=demo_headers, json={"name": "TEST_QA_Agent"})
        assert r.status_code in (200, 201), f"create agent failed: {r.status_code} {r.text}"
        a = r.json()
        assert a.get("id")
        assert a.get("paired") in (False, None) or a.get("paired") is False
        assert a.get("pairing_code"), "pairing_code missing on unpaired agent"
        assert len(str(a["pairing_code"])) >= 4
        # cleanup handled by dedicated test below
        pytest.agent_id = a["id"]

    def test_download_returns_zip(self, client, demo_headers):
        r = client.get(f"{API}/bridge/agent/download", headers=demo_headers)
        assert r.status_code == 200, f"download failed: {r.status_code} {r.text[:200]}"
        ct = r.headers.get("Content-Type", "")
        assert "zip" in ct.lower(), f"unexpected content-type: {ct}"
        # Verify zip integrity
        z = zipfile.ZipFile(io.BytesIO(r.content))
        names = z.namelist()
        assert any(n.startswith("ordia-bridge/") for n in names), f"unexpected zip contents: {names[:5]}"
        # Should contain agent.py or Dockerfile
        assert any("agent.py" in n or "Dockerfile" in n for n in names), \
            f"zip missing bridge files: {names[:10]}"

    def test_download_requires_auth(self, client):
        r = requests.get(f"{API}/bridge/agent/download")
        assert r.status_code in (401, 403)

    def test_delete_created_agent(self, client, demo_headers):
        agent_id = getattr(pytest, "agent_id", None)
        if not agent_id:
            pytest.skip("no agent to delete")
        r = client.delete(f"{API}/bridge/agents/{agent_id}", headers=demo_headers)
        assert r.status_code in (200, 204)


# ---------- order creation via text import + line update ----------
class TestOrders:
    def test_create_from_text_and_update_line(self, client, demo_token):
        # Use multipart form (endpoint is /orders/extract with source_type=text)
        text = "Ciao, per domani mandami 10 casse di pomodori pelati e 5 kg di mozzarella"
        h = {"Authorization": f"Bearer {demo_token}"}
        r = requests.post(
            f"{API}/orders/extract",
            headers=h,
            data={"source_type": "text", "text": text},
            timeout=90,
        )
        assert r.status_code in (200, 201), f"extract failed: {r.status_code} {r.text[:300]}"
        order = r.json()
        oid = order.get("id")
        assert oid, f"no order id: {order}"
        items = order.get("line_items") or []
        assert len(items) > 0, f"no extracted line items from AI: {order}"

        # Update qty of first line via PUT /orders/{id}
        first = dict(items[0])
        original_qty = first.get("quantity") or 1
        new_qty = original_qty + 3
        first["quantity"] = new_qty
        upd_body = {"line_items": [first] + [dict(x) for x in items[1:]]}
        upd = requests.put(
            f"{API}/orders/{oid}",
            headers={**h, "Content-Type": "application/json"},
            json=upd_body,
            timeout=30,
        )
        assert upd.status_code in (200, 204), f"line update failed: {upd.status_code} {upd.text[:200]}"

        # Verify persisted
        g2 = requests.get(f"{API}/orders/{oid}", headers=h)
        assert g2.status_code == 200
        got_items = g2.json().get("line_items") or []
        assert got_items[0].get("quantity") == new_qty, \
            f"qty not persisted, expected {new_qty} got {got_items[0].get('quantity')}"
