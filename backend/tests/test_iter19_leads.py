"""
Iteration 19 — Waitlist / Early-access lead capture (GLOBAL-FIRST, GDPR).

Covers:
- POST /api/leads valid create -> {ok:true, already:false}
- Missing consent -> HTTP 400
- Invalid email -> HTTP 400
- CF-IPCountry header -> stored country
- Phone-prefix fallback (+39 -> IT)
- Idempotent + non-destructive dedupe
- Admin-only GET /api/leads (401 without auth, 200 with admin token)
- created_at is UTC ISO string, sorted desc

Cleanup: deletes all TEST_iter19_* leads AND the pre-existing test leads
(mario@example.com, lucia@example.com, hans@example.de) after run.
"""
import os
import time
import uuid
import pytest
import requests
from datetime import datetime

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "demo@ordia.app"
ADMIN_PASSWORD = "demo123"

# Emails to purge after the test run (test-created + pre-existing dev seeds)
CLEANUP_EMAILS = {
    "mario@example.com",
    "lucia@example.com",
    "hans@example.de",
}
# Test-created emails will be appended dynamically
TEST_EMAILS_CREATED = set()


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_token():
    # Use a throw-away session so we don't pollute the anonymous `session` fixture
    # with the login cookie (Set-Cookie: ordia_token=...) that the login endpoint
    # returns. That cookie would otherwise leak into `session` and break the
    # 401-without-auth test.
    tmp = requests.Session()
    r = tmp.post(f"{API}/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
    })
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("token") or data.get("access_token")
    if not tok:
        pytest.skip("No token in login response")
    return tok


@pytest.fixture(scope="module")
def admin_session(admin_token):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}",
    })
    return s


def _mk_email(tag: str) -> str:
    e = f"test_iter19_{tag}_{uuid.uuid4().hex[:8]}@example.com"
    TEST_EMAILS_CREATED.add(e)
    return e


# ---------------------------------------------------------------------------
# POST /api/leads — basic happy path
# ---------------------------------------------------------------------------
class TestLeadCreate:
    def test_valid_submission(self, session):
        email = _mk_email("valid")
        r = session.post(f"{API}/leads", json={
            "email": email,
            "company_name": "TEST_iter19 Foods",
            "phone": "+393331234567",
            "consent": True,
            "locale": "en",
            "source": "test_iter19",
        })
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        data = r.json()
        assert data.get("ok") is True
        assert data.get("already") is False

    def test_missing_consent_rejected(self, session):
        email = _mk_email("noconsent")
        r = session.post(f"{API}/leads", json={
            "email": email,
            "consent": False,
        })
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"
        # Also try consent omitted entirely
        email2 = _mk_email("noconsent2")
        r2 = session.post(f"{API}/leads", json={"email": email2})
        assert r2.status_code == 400

    def test_invalid_email_rejected(self, session):
        r = session.post(f"{API}/leads", json={
            "email": "not-an-email",
            "consent": True,
        })
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"
        r2 = session.post(f"{API}/leads", json={
            "email": "missing-at-sign.example.com",
            "consent": True,
        })
        assert r2.status_code == 400


# ---------------------------------------------------------------------------
# Country detection
# ---------------------------------------------------------------------------
class TestCountryDetection:
    def test_cf_ipcountry_header_wins(self, admin_session):
        """
        Verify backend correctly reads CF-IPCountry header. NOTE: The public
        preview ingress strips inbound CF-IPCountry headers to prevent client
        spoofing (standard Cloudflare behavior — the real Cloudflare edge sets
        this header in production). So we exercise the code path by hitting the
        backend directly on localhost:8001. The application code at
        server.py:571 is what we're validating.
        """
        import requests as _req
        email = _mk_email("cfde")
        r = _req.post("http://localhost:8001/api/leads",
            headers={"CF-IPCountry": "DE", "Content-Type": "application/json"},
            json={
                "email": email,
                "phone": "+393331234567",  # would resolve to IT via fallback
                "consent": True,
                "locale": "en",
            })
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        time.sleep(0.3)
        # Verify via admin GET on the same origin so it sees the same DB
        lst = admin_session.get(f"{API}/leads").json()
        found = next((x for x in lst["items"] if x["email"] == email), None)
        assert found is not None, "Lead not found in admin list"
        assert found.get("country") == "DE", \
            f"CF-IPCountry=DE header should override phone-prefix fallback; got {found.get('country')}"

    def test_phone_prefix_fallback_it(self, session, admin_session):
        email = _mk_email("phoneit")
        r = session.post(f"{API}/leads", json={
            "email": email,
            "phone": "+393479998888",
            "consent": True,
            "locale": "it",
        })
        assert r.status_code == 200
        time.sleep(0.3)
        lst = admin_session.get(f"{API}/leads").json()
        found = next((x for x in lst["items"] if x["email"] == email), None)
        assert found is not None
        assert found.get("country") == "IT", f"Expected IT, got {found.get('country')}"


# ---------------------------------------------------------------------------
# Dedupe: idempotent + non-destructive
# ---------------------------------------------------------------------------
class TestDedupe:
    def test_dedupe_idempotent_and_nondestructive(self, session, admin_session):
        email = _mk_email("dedupe")
        # 1st POST: full payload
        r1 = session.post(f"{API}/leads", json={
            "email": email,
            "company_name": "TEST_iter19 Company A",
            "phone": "+393331112222",
            "consent": True,
            "locale": "en",
        })
        assert r1.status_code == 200
        assert r1.json().get("already") is False

        # 2nd POST: same email, empty phone/company (must NOT wipe existing)
        r2 = session.post(f"{API}/leads", json={
            "email": email,
            "company_name": "",
            "phone": "",
            "consent": True,
            "locale": "en",
        })
        assert r2.status_code == 200
        j2 = r2.json()
        assert j2.get("ok") is True
        assert j2.get("already") is True, f"Expected already:true on 2nd call, got {j2}"

        # Verify: still one lead with company/phone/country preserved
        time.sleep(0.3)
        lst = admin_session.get(f"{API}/leads").json()
        matching = [x for x in lst["items"] if x["email"] == email]
        assert len(matching) == 1, f"Expected exactly 1 lead, got {len(matching)}"
        lead = matching[0]
        assert lead.get("company_name") == "TEST_iter19 Company A", \
            f"Company got wiped: {lead.get('company_name')}"
        assert lead.get("phone") == "+393331112222", \
            f"Phone got wiped: {lead.get('phone')}"
        assert lead.get("country") == "IT", \
            f"Country got wiped: {lead.get('country')}"


# ---------------------------------------------------------------------------
# GET /api/leads — admin only + response shape
# ---------------------------------------------------------------------------
class TestListLeadsAdmin:
    def test_unauthenticated_rejected(self, session):
        r = session.get(f"{API}/leads")
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code} {r.text}"

    def test_admin_can_list(self, admin_session):
        r = admin_session.get(f"{API}/leads")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data and "total" in data
        assert isinstance(data["items"], list)
        assert data["total"] == len(data["items"])

    def test_created_at_is_utc_iso_and_sorted_desc(self, session, admin_session):
        # Create two leads to check ordering
        e1 = _mk_email("sort_a")
        session.post(f"{API}/leads", json={"email": e1, "consent": True, "locale": "en"})
        time.sleep(1.1)  # ensure created_at differs
        e2 = _mk_email("sort_b")
        session.post(f"{API}/leads", json={"email": e2, "consent": True, "locale": "en"})
        time.sleep(0.3)

        data = admin_session.get(f"{API}/leads").json()
        items = data["items"]
        assert len(items) >= 2

        # created_at should be ISO string
        first = items[0]
        assert isinstance(first["created_at"], str)
        # Must be parseable as ISO
        parsed = datetime.fromisoformat(first["created_at"].replace("Z", "+00:00"))
        assert parsed.tzinfo is not None, "created_at must be timezone-aware (UTC)"

        # Check sort desc by created_at
        ts = [datetime.fromisoformat(x["created_at"].replace("Z", "+00:00")) for x in items]
        assert ts == sorted(ts, reverse=True), "leads must be sorted by created_at desc"

        # e2 (later) should appear before e1
        idx1 = next(i for i, x in enumerate(items) if x["email"] == e1)
        idx2 = next(i for i, x in enumerate(items) if x["email"] == e2)
        assert idx2 < idx1, "Newer lead should appear before older"


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module", autouse=True)
def _cleanup_after_all(admin_session):
    yield
    # After all tests: delete every test lead + pre-existing dev seeds directly via DB.
    try:
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ["MONGO_URL"]
        db_name = os.environ["DB_NAME"]

        async def _purge():
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            to_delete = list(CLEANUP_EMAILS | TEST_EMAILS_CREATED)
            res = await db.leads.delete_many({"email": {"$in": to_delete}})
            print(f"[cleanup] deleted {res.deleted_count} lead(s): {to_delete}")
            client.close()

        asyncio.run(_purge())
    except Exception as e:
        print(f"[cleanup] WARNING: could not purge test leads via Mongo: {e}")
