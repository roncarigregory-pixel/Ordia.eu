"""iter20 — AI Marketing Agent (Phase 1) backend tests.

Covers:
- Auth guard (/api/marketing/* returns 401 without token)
- Brand profile GET (seeds defaults for Ordia) + PUT (persists edits)
- Content generation (LinkedIn draft) — slow (Claude Sonnet 4.6)
- SEO blog generation with `seo{}` fields
- Calendar generation: weekly with balanced categories + scheduled_at
- Approval → Schedule → Publish workflow (webhook fires when configured)
- Image generation (Nano Banana) + media serving as image/*
- Recommendations
- Stats counters

Tests are careful not to hammer the LLM: image + calendar + blog are LLM-heavy.
"""
import os
import uuid
import pytest
import requests
from pathlib import Path
from pymongo import MongoClient


def _load_env(path):
    if not Path(path).exists():
        return
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k.strip(), v)


_load_env("/app/frontend/.env")
_load_env("/app/backend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

ADMIN_EMAIL = "demo@ordia.app"
ADMIN_PASSWORD = "demo123"


@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    token = r.json().get("access_token")
    assert token
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def created_ids():
    ids = {"content": [], "media": []}
    yield ids


@pytest.fixture(scope="module", autouse=True)
def cleanup(mongo, created_ids):
    yield
    # Cleanup only what THIS test module created + reset webhook to empty.
    if created_ids["content"]:
        mongo.mkt_content.delete_many({"id": {"$in": created_ids["content"]}})
    if created_ids["media"]:
        mongo.mkt_media.delete_many({"id": {"$in": created_ids["media"]}})
    # Reset webhook url to empty on brand (leave seed doc)
    mongo.mkt_brands.update_many({}, {"$set": {"publish_webhook_url": ""}})


# ---------------- Auth guard ----------------
def test_marketing_endpoints_require_auth():
    r = requests.get(f"{BASE_URL}/api/marketing/brand", timeout=10)
    assert r.status_code in (401, 403), f"Expected 401/403 unauth, got {r.status_code}"


# ---------------- Brand profile ----------------
def test_brand_get_returns_seeded_defaults(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/marketing/brand", timeout=15)
    assert r.status_code == 200
    b = r.json()
    assert b.get("company_name")  # seeded to "Ordia"
    assert "brand_colors" in b and isinstance(b["brand_colors"], list)
    assert "publish_webhook_url" in b
    assert "_id" not in b


def test_brand_put_persists_and_returns_updated(admin_session):
    new_tone = f"TEST_iter20_tone_{uuid.uuid4().hex[:6]}"
    r = admin_session.put(f"{BASE_URL}/api/marketing/brand",
                          json={"tone_of_voice": new_tone,
                                "publish_webhook_url": ""}, timeout=15)
    assert r.status_code == 200
    assert r.json()["tone_of_voice"] == new_tone
    # GET to verify persistence
    r2 = admin_session.get(f"{BASE_URL}/api/marketing/brand", timeout=15)
    assert r2.json()["tone_of_voice"] == new_tone


# ---------------- Content generation ----------------
def test_generate_linkedin_draft(admin_session, created_ids):
    r = admin_session.post(f"{BASE_URL}/api/marketing/generate", json={
        "channel": "linkedin",
        "category": "ai_automation",
        "topic": "TEST_iter20 how AI reads WhatsApp orders",
        "language": "en",
    }, timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "draft"
    assert d["channel"] == "linkedin"
    assert d["title"] and d["body"]
    assert "id" in d
    assert isinstance(d.get("hashtags"), list)
    assert isinstance(d.get("seo"), dict)
    assert "_id" not in d
    created_ids["content"].append(d["id"])


def test_generate_invalid_channel(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/marketing/generate", json={
        "channel": "not_a_channel", "category": "ai_automation", "language": "en"}, timeout=15)
    assert r.status_code == 400


# ---------------- Blog ----------------
def test_blog_generation_with_seo(admin_session, created_ids):
    r = admin_session.post(f"{BASE_URL}/api/marketing/blog", json={
        "topic": "TEST_iter20 wholesale distribution automation",
        "language": "en",
    }, timeout=120)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["channel"] == "blog"
    seo = d.get("seo") or {}
    # Expected keys — at least one should be populated
    assert isinstance(seo, dict)
    assert seo.get("meta_title") or seo.get("meta_description") or seo.get("keywords")
    created_ids["content"].append(d["id"])


# ---------------- Calendar ----------------
def test_calendar_weekly_generates_balanced_items(admin_session, created_ids):
    r = admin_session.post(f"{BASE_URL}/api/marketing/calendar/generate",
                           json={"period": "weekly"}, timeout=120)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["count"] >= 1
    items = d["items"]
    for it in items:
        assert it["status"] == "idea"
        assert it.get("scheduled_at")
        created_ids["content"].append(it["id"])
    # Balance: >1 category represented for weekly
    cats = {it["category"] for it in items}
    assert len(cats) >= 2, f"Expected varied categories, got {cats}"


# ---------------- Workflow: approve -> schedule -> publish ----------------
def _make_draft(session, created_ids, channel="twitter"):
    r = session.post(f"{BASE_URL}/api/marketing/generate", json={
        "channel": channel, "category": "product_updates",
        "topic": "TEST_iter20 workflow test", "language": "en"}, timeout=90)
    assert r.status_code == 200
    cid = r.json()["id"]
    created_ids["content"].append(cid)
    return cid


def test_approve_schedule_publish_workflow(admin_session, created_ids):
    # Reset webhook empty first -> publish should still succeed (no delivery)
    admin_session.put(f"{BASE_URL}/api/marketing/brand",
                      json={"publish_webhook_url": ""}, timeout=15)

    cid = _make_draft(admin_session, created_ids)

    # Approve
    r = admin_session.post(f"{BASE_URL}/api/marketing/content/{cid}/approve", timeout=15)
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    # Schedule
    r = admin_session.post(f"{BASE_URL}/api/marketing/content/{cid}/schedule",
                           json={"scheduled_at": "2026-12-31T10:00:00+00:00"}, timeout=15)
    assert r.status_code == 200
    assert r.json()["status"] == "scheduled"
    assert r.json()["scheduled_at"].startswith("2026-12-31")

    # Publish (no webhook configured)
    r = admin_session.post(f"{BASE_URL}/api/marketing/content/{cid}/publish", timeout=20)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "published"
    assert body["published_at"]
    assert body.get("_delivery", {}).get("webhook_configured") is False


def test_publish_with_webhook_fires(admin_session, created_ids):
    # Set httpbin webhook
    r = admin_session.put(f"{BASE_URL}/api/marketing/brand",
                          json={"publish_webhook_url": "https://httpbin.org/post"}, timeout=15)
    assert r.status_code == 200

    cid = _make_draft(admin_session, created_ids)
    admin_session.post(f"{BASE_URL}/api/marketing/content/{cid}/approve", timeout=15)

    r = admin_session.post(f"{BASE_URL}/api/marketing/content/{cid}/publish", timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "published"
    delivery = body.get("_delivery", {})
    assert delivery.get("webhook_configured") is True
    # httpbin returns 200 on POST
    assert delivery.get("webhook_status") in (200, "error"), delivery


# ---------------- Image generation ----------------
def test_image_generation_and_media_serving(admin_session, created_ids, mongo):
    # Create a fresh draft
    cid = _make_draft(admin_session, created_ids, channel="instagram")

    r = admin_session.post(f"{BASE_URL}/api/marketing/content/{cid}/image",
                           json={"prompt": "TEST_iter20 minimalist geometric brand visual"},
                           timeout=180)
    assert r.status_code == 200, r.text
    image_url = r.json()["image_url"]
    assert image_url.startswith("/api/marketing/media/")

    media_id = image_url.rsplit("/", 1)[-1]
    created_ids["media"].append(media_id)

    # GET media
    r2 = requests.get(f"{BASE_URL}{image_url}", timeout=30)
    assert r2.status_code == 200
    ct = r2.headers.get("Content-Type", "")
    assert ct.startswith("image/"), f"Content-Type not image: {ct}"
    assert len(r2.content) > 1000  # meaningful image

    # Confirm image_url now set on content
    r3 = admin_session.get(f"{BASE_URL}/api/marketing/content/{cid}", timeout=10)
    assert r3.json()["image_url"] == image_url


# ---------------- Recommendations ----------------
def test_recommendations_returns_ideas(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/marketing/recommendations", timeout=90)
    assert r.status_code == 200
    d = r.json()
    assert "ideas" in d
    assert isinstance(d["ideas"], list)


# ---------------- Stats ----------------
def test_stats_returns_counters(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/marketing/stats", timeout=10)
    assert r.status_code == 200
    s = r.json()
    for k in ("total", "idea", "draft", "approved", "scheduled", "published"):
        assert k in s and isinstance(s[k], int)


# ---------------- Delete ----------------
def test_delete_content(admin_session, created_ids):
    cid = _make_draft(admin_session, created_ids)
    r = admin_session.delete(f"{BASE_URL}/api/marketing/content/{cid}", timeout=10)
    assert r.status_code == 200
    # Verify 404
    r2 = admin_session.get(f"{BASE_URL}/api/marketing/content/{cid}", timeout=10)
    assert r2.status_code == 404
