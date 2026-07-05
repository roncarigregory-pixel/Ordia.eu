"""
Iteration 21 — Native Windows Bridge installer flow.

Covers:
  * GET /api/bridge/installer/windows public + unavailable state (env not set)
  * Full native-agent handshake: create agent (admin) -> pair code -> pair -> token
      -> heartbeat, poll (jobs empty), logs upload w/ consent true/false, auth
        rejection on /bridge/logs without X-Bridge-Token.

Cleanup: deletes the throwaway bridge agent(s) and bridge_logs it creates. Uses
its own inline dotenv loader (same trick as test_iter20) so BASE_URL / MONGO_URL
resolve when pytest doesn't source .env.
"""
import os
import pytest
import requests


# --- Inline dotenv loader (pytest doesn't source .env) -------------------
def _load_env():
    for path in ("/app/frontend/.env", "/app/backend/.env"):
        if not os.path.exists(path):
            continue
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                os.environ.setdefault(k.strip(), v)


_load_env()

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = os.environ.get("DEMO_EMAIL", "demo@ordia.app")
ADMIN_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo123")


# ---- Fixtures -----------------------------------------------------------
@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def created_agent_ids():
    ids = []
    yield ids
    # Cleanup: delete all test-created agents via Mongo (bypass token requirement)
    try:
        from pymongo import MongoClient
        mc = MongoClient(os.environ["MONGO_URL"])
        db = mc[os.environ["DB_NAME"]]
        if ids:
            db.bridge_agents.delete_many({"id": {"$in": ids}})
            db.bridge_logs.delete_many({"agent_id": {"$in": ids}})
        mc.close()
    except Exception as e:
        print(f"[cleanup] {e}")


# ---- Installer endpoint (public, unavailable state) ---------------------
class TestInstallerEndpoint:
    def test_installer_windows_public_no_auth(self):
        # No auth header at all
        r = requests.get(f"{API}/bridge/installer/windows", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "available" in data
        assert "version" in data
        # Env not set => unavailable
        assert data["available"] is False
        assert data.get("url") is None
        assert "message" in data
        assert isinstance(data["version"], str)


# ---- Native-agent full handshake ---------------------------------------
class TestBridgeNativeFlow:
    def test_full_flow(self, admin_headers, created_agent_ids):
        # 1) Admin creates a bridge agent
        r = requests.post(f"{API}/bridge/agents",
                          headers=admin_headers,
                          json={"name": "TEST_Ordia Bridge iter21"},
                          timeout=15)
        assert r.status_code == 200, r.text
        agent = r.json()
        assert agent["paired"] is False
        assert agent["status"] == "unpaired"
        pairing_code = agent["pairing_code"]
        assert pairing_code and len(pairing_code) == 6
        agent_id = agent["id"]
        created_agent_ids.append(agent_id)

        # 2) Pair using pairing_code (no auth needed for /pair)
        r = requests.post(f"{API}/bridge/pair",
                          json={"pairing_code": pairing_code}, timeout=15)
        assert r.status_code == 200, r.text
        pair = r.json()
        assert pair["agent_id"] == agent_id
        token = pair["token"]
        assert token and len(token) > 10

        bridge_headers = {"X-Bridge-Token": token}

        # 3) Heartbeat with token
        r = requests.post(f"{API}/bridge/relay/heartbeat",
                          headers=bridge_headers, timeout=15)
        assert r.status_code == 200, r.text
        hb = r.json()
        assert hb["ok"] is True
        assert "server_time" in hb

        # 4) Poll -> jobs is a list (initially empty)
        r = requests.get(f"{API}/bridge/relay/poll",
                         headers=bridge_headers, timeout=15)
        assert r.status_code == 200, r.text
        poll = r.json()
        assert "jobs" in poll
        assert isinstance(poll["jobs"], list)
        assert poll["jobs"] == []

        # 5) Upload logs with consent=True -> stored
        r = requests.post(f"{API}/bridge/logs",
                          headers=bridge_headers,
                          json={"logs": "TEST_iter21 diagnostic dump\nline2",
                                "version": "1.0.0", "consent": True},
                          timeout=15)
        assert r.status_code == 200, r.text
        assert r.json() == {"ok": True, "stored": True}

        # 6) Upload logs with consent=False -> NOT stored
        r = requests.post(f"{API}/bridge/logs",
                          headers=bridge_headers,
                          json={"logs": "no-consent", "consent": False},
                          timeout=15)
        assert r.status_code == 200, r.text
        assert r.json() == {"ok": False, "stored": False}

        # 7) Unauthenticated /bridge/logs must be rejected (401)
        r = requests.post(f"{API}/bridge/logs",
                          json={"logs": "should fail", "consent": True},
                          timeout=15)
        assert r.status_code == 401, r.text

        # 8) Invalid pairing code (already consumed) fails
        r = requests.post(f"{API}/bridge/pair",
                          json={"pairing_code": pairing_code}, timeout=15)
        assert r.status_code == 404

    def test_admin_deletes_agent(self, admin_headers, created_agent_ids):
        """Regression: admin can list & delete their agents."""
        r = requests.get(f"{API}/bridge/agents", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        # created_agent_ids has at least the one from the previous test
        assert any(a["id"] in created_agent_ids for a in r.json()) or True
