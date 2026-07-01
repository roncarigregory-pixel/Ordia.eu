"""
Iteration 5 regression tests.

Verifies that after:
 (a) CORS middleware change: allow_credentials=False, allow_origins from CORS_ORIGINS env
 (b) Frontend useCallback hook-dep fixes on 5 pages (Catalog, TeamSetup, EmailSetup,
     ErpSetup, LearningSetup)
the backend auth flow (Bearer via Authorization header) and the core pipeline plus
Milestone 2 (WhatsApp webhook + Email poll gating) still work end-to-end.
"""

import os
import uuid
import requests
import pytest
from pathlib import Path


def _load_frontend_env():
    env_path = Path("/app/frontend/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_frontend_env()
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


# ---------- Auth / CORS behavior ----------

class TestAuthAfterCorsChange:
    def test_login_demo_returns_token(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": "demo@ordia.app", "password": "demo123"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "access_token" in data and isinstance(data["access_token"], str) and len(data["access_token"]) > 20
        assert data["user"]["email"] == "demo@ordia.app"

    def test_me_with_bearer(self):
        tok = requests.post(f"{API}/auth/login",
                            json={"email": "demo@ordia.app", "password": "demo123"}).json()["access_token"]
        r = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 200, r.text
        assert r.json()["email"] == "demo@ordia.app"

    def test_protected_requires_bearer(self):
        # Without token → 401/403
        r = requests.get(f"{API}/products")
        assert r.status_code in (401, 403), r.text

        tok = requests.post(f"{API}/auth/login",
                            json={"email": "demo@ordia.app", "password": "demo123"}).json()["access_token"]
        r2 = requests.get(f"{API}/products", headers={"Authorization": f"Bearer {tok}"})
        assert r2.status_code == 200, r2.text
        assert isinstance(r2.json(), list)

    def test_cors_headers_no_credentials(self):
        # Simulated cross-origin preflight
        r = requests.options(
            f"{API}/auth/login",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization",
            },
        )
        # Header should NOT advertise credentials since allow_credentials=False
        assert r.headers.get("access-control-allow-credentials", "false").lower() != "true"


# ---------- Fixture: authed session on demo tenant ----------

@pytest.fixture(scope="module")
def demo_headers():
    tok = requests.post(f"{API}/auth/login",
                        json={"email": "demo@ordia.app", "password": "demo123"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


# ---------- Data-loading endpoints for the 5 refactored pages ----------

class TestPageDataLoads:
    def test_catalog_loads_and_crud(self, demo_headers):
        # LIST
        before = requests.get(f"{API}/products", headers=demo_headers).json()
        assert isinstance(before, list) and len(before) > 0  # seeded catalog

        # CREATE
        sku = f"TEST_{uuid.uuid4().hex[:6]}"
        payload = {"sku": sku, "name": "TEST Prodotto Iter5", "category": "General",
                   "unit": "unità", "pack_size": "1", "price": 1.23, "aliases": ["testalias"]}
        r = requests.post(f"{API}/products", json=payload, headers=demo_headers)
        assert r.status_code in (200, 201), r.text
        pid = r.json()["id"]
        assert r.json()["sku"] == sku

        # GET verify persistence
        after = requests.get(f"{API}/products", headers=demo_headers).json()
        assert any(p["id"] == pid for p in after)

        # DELETE
        rd = requests.delete(f"{API}/products/{pid}", headers=demo_headers)
        assert rd.status_code in (200, 204)
        after2 = requests.get(f"{API}/products", headers=demo_headers).json()
        assert not any(p["id"] == pid for p in after2)

    def test_team_loads_and_add(self, demo_headers):
        r = requests.get(f"{API}/team", headers=demo_headers)
        assert r.status_code == 200
        members_before = r.json()
        assert isinstance(members_before, list) and len(members_before) >= 1

        email = f"TEST_{uuid.uuid4().hex[:6]}@example.com"
        payload = {"name": "TEST Iter5", "email": email, "password": "secret123", "role": "operator"}
        r2 = requests.post(f"{API}/team", json=payload, headers=demo_headers)
        assert r2.status_code in (200, 201), r2.text

        members_after = requests.get(f"{API}/team", headers=demo_headers).json()
        added = [m for m in members_after if m["email"] == email.lower()]
        assert len(added) == 1
        mid = added[0]["id"]

        # Role change
        r3 = requests.put(f"{API}/team/{mid}/role", json={"role": "sales"}, headers=demo_headers)
        assert r3.status_code == 200, r3.text
        m = [x for x in requests.get(f"{API}/team", headers=demo_headers).json() if x["id"] == mid][0]
        assert m["role"] == "sales"

        # cleanup
        requests.delete(f"{API}/team/{mid}", headers=demo_headers)

    def test_email_setup_loads(self, demo_headers):
        r = requests.get(f"{API}/integrations/email", headers=demo_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        # forwarding_address should be present (demo tenant is provisioned)
        assert "forwarding_address" in data

    def test_erp_setup_loads(self, demo_headers):
        r = requests.get(f"{API}/integrations/erp", headers=demo_headers)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), dict)

    def test_learning_loads(self, demo_headers):
        r = requests.get(f"{API}/learning", headers=demo_headers)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)


# ---------- Milestone 2 regression: WhatsApp webhook + Email gating ----------

class TestMilestone2Regression:
    def test_whatsapp_full_flow(self, demo_headers):
        phone_id = f"pid_{uuid.uuid4().hex[:10]}"
        verify_token = f"vt_{uuid.uuid4().hex[:8]}"
        create = requests.post(
            f"{API}/integrations/whatsapp",
            json={
                "phone_number_id": phone_id,
                "access_token": "DUMMY_TOKEN",
                "verify_token": verify_token,
                "app_secret": "dummy_secret",
                "waba_id": "biz_1",
            },
            headers=demo_headers,
        )
        assert create.status_code in (200, 201), create.text

        # VERIFY handshake
        v = requests.get(
            f"{API}/webhooks/whatsapp",
            params={"hub.mode": "subscribe", "hub.verify_token": verify_token, "hub.challenge": "12345"},
        )
        assert v.status_code == 200
        assert v.text.strip('"') == "12345"

        # RECEIVE text
        msg_id = f"wamid.TEST_{uuid.uuid4().hex[:10]}"
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": phone_id},
                        "messages": [{
                            "id": msg_id,
                            "from": "393401112233",
                            "type": "text",
                            "text": {"body": "Ciao, 3 casse mozzarella e 2 sacchi farina"},
                        }],
                    }
                }]
            }]
        }
        p1 = requests.post(f"{API}/webhooks/whatsapp", json=payload)
        assert p1.status_code == 200, p1.text
        assert p1.json().get("orders_created") == 1

        # Idempotency
        p2 = requests.post(f"{API}/webhooks/whatsapp", json=payload)
        assert p2.status_code == 200
        assert p2.json().get("orders_created") == 0

    def test_email_poll_gating_before_connect(self):
        # Register a fresh tenant so state is clean
        email = f"TEST_email_{uuid.uuid4().hex[:6]}@example.com"
        reg = requests.post(f"{API}/auth/register", json={
            "company_name": "TEST Co Iter5", "name": "TEST", "email": email, "password": "secret123"
        })
        assert reg.status_code in (200, 201), reg.text
        tok = reg.json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}

        r = requests.post(f"{API}/integrations/email/poll", headers=h)
        assert r.status_code == 400, r.text


# ---------- Core pipeline regression ----------

class TestPipelineRegression:
    def test_extract_validate_learning_export(self, demo_headers):
        learning_before = requests.get(f"{API}/learning", headers=demo_headers).json()
        n_before = len(learning_before)

        # extract via text
        phrase = f"Buongiorno, 5 casse mozzarella e 1 sacco farina - TEST_{uuid.uuid4().hex[:6]}"
        r = requests.post(
            f"{API}/orders/extract",
            data={"source_type": "text", "text": phrase},
            headers=demo_headers,
        )
        assert r.status_code in (200, 201), r.text
        order = r.json()
        oid = order["id"]

        # validate → grow learning
        v = requests.post(f"{API}/orders/{oid}/validate", headers=demo_headers)
        assert v.status_code == 200, v.text

        learning_after = requests.get(f"{API}/learning", headers=demo_headers).json()
        assert len(learning_after) >= n_before  # non-decreasing (may be same if no new alias)

        # export
        rc = requests.get(f"{API}/orders/{oid}/export", params={"format": "csv"}, headers=demo_headers)
        assert rc.status_code == 200
        assert "text/csv" in rc.headers.get("content-type", "") or rc.text.count(",") > 0

        rj = requests.get(f"{API}/orders/{oid}/export", params={"format": "json"}, headers=demo_headers)
        assert rj.status_code == 200
        assert isinstance(rj.json(), dict)

    def test_dashboard_stats(self, demo_headers):
        r = requests.get(f"{API}/dashboard/stats", headers=demo_headers)
        assert r.status_code == 200, r.text
        stats = r.json()
        assert isinstance(stats, dict)
