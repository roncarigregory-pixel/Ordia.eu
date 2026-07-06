"""Backend tests — Iter25 Ordini Dashboard Operativa

Tests for GET /api/orders enhancements:
- Response includes summary {green, amber, red}
- Each order has bucket, reliability, review_count fields
- ?bucket=green|amber|red filter
- ?sort=critical (red→amber→green→done, within bucket by reliability asc)
- ?sort=recent (default: by created_at desc)
- Counter coherence: summary.<b> == count of orders with bucket=<b> across the company
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

DEMO_EMAIL = "demo@ordia.app"
DEMO_PASSWORD = "demo123"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def token(api):
    r = api.post(f"{BASE_URL}/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token")
    assert tok, f"No access_token in login response: {data}"
    return tok


@pytest.fixture(scope="module")
def auth(api, token):
    api.headers.update({"Authorization": f"Bearer {token}"})
    return api


class TestOrdersOpsDashboard:
    def test_orders_response_has_summary_and_computed_fields(self, auth):
        r = auth.get(f"{BASE_URL}/api/orders", params={"limit": 200})
        assert r.status_code == 200, r.text
        data = r.json()
        # Summary present with all buckets
        assert "summary" in data, "response missing 'summary'"
        s = data["summary"]
        for k in ("green", "amber", "red"):
            assert k in s, f"summary missing '{k}': {s}"
            assert isinstance(s[k], int), f"summary.{k} should be int, got {type(s[k])}"
        # Items have computed fields
        items = data["items"]
        assert isinstance(items, list)
        for o in items:
            assert "bucket" in o, f"order {o.get('id')} missing bucket"
            assert o["bucket"] in ("green", "amber", "red", "done", "pending"), o["bucket"]
            assert "reliability" in o
            assert isinstance(o["reliability"], int)
            assert 0 <= o["reliability"] <= 100
            assert "review_count" in o
            assert isinstance(o["review_count"], int)

    def test_filter_bucket_amber_returns_only_amber(self, auth):
        r = auth.get(f"{BASE_URL}/api/orders", params={"bucket": "amber", "status": "all", "limit": 200})
        assert r.status_code == 200
        data = r.json()
        for o in data["items"]:
            assert o["bucket"] == "amber", f"Non-amber order returned: {o.get('id')} bucket={o['bucket']}"
        # total matches items count for capped page
        assert data["total"] == len(data["items"]) or data["total"] >= len(data["items"])

    def test_filter_bucket_green_returns_only_green(self, auth):
        r = auth.get(f"{BASE_URL}/api/orders", params={"bucket": "green", "status": "all", "limit": 200})
        assert r.status_code == 200
        data = r.json()
        for o in data["items"]:
            assert o["bucket"] == "green", f"Non-green order returned: {o.get('id')} bucket={o['bucket']}"

    def test_filter_bucket_red_returns_only_red(self, auth):
        r = auth.get(f"{BASE_URL}/api/orders", params={"bucket": "red", "status": "all", "limit": 200})
        assert r.status_code == 200
        data = r.json()
        for o in data["items"]:
            assert o["bucket"] == "red", f"Non-red order returned: {o.get('id')} bucket={o['bucket']}"

    def test_sort_critical_orders_red_amber_green_done(self, auth):
        r = auth.get(f"{BASE_URL}/api/orders", params={"sort": "critical", "status": "all", "limit": 200})
        assert r.status_code == 200
        items = r.json()["items"]
        order_map = {"red": 0, "amber": 1, "green": 2, "pending": 3, "done": 4}
        # Check bucket ordering
        buckets = [o["bucket"] for o in items]
        bucket_ranks = [order_map.get(b, 9) for b in buckets]
        assert bucket_ranks == sorted(bucket_ranks), f"Buckets not sorted red→amber→green→done: {buckets}"
        # Within same bucket, reliability ASC
        by_bucket = {}
        for o in items:
            by_bucket.setdefault(o["bucket"], []).append(o["reliability"])
        for b, rels in by_bucket.items():
            assert rels == sorted(rels), f"Within bucket '{b}', reliability not ascending: {rels}"

    def test_sort_recent_orders_by_created_at_desc(self, auth):
        r = auth.get(f"{BASE_URL}/api/orders", params={"sort": "recent", "status": "all", "limit": 200})
        assert r.status_code == 200
        items = r.json()["items"]
        dates = [o.get("created_at") for o in items]
        assert dates == sorted(dates, reverse=True), f"Not sorted by created_at desc: {dates}"

    def test_default_sort_is_recent(self, auth):
        r = auth.get(f"{BASE_URL}/api/orders", params={"status": "all", "limit": 200})
        assert r.status_code == 200
        items = r.json()["items"]
        dates = [o.get("created_at") for o in items]
        assert dates == sorted(dates, reverse=True), "Default sort should be by created_at desc"

    def test_summary_counts_match_bucket_filter_counts(self, auth):
        # Get overall summary
        r_all = auth.get(f"{BASE_URL}/api/orders", params={"status": "all", "limit": 200})
        summary = r_all.json()["summary"]

        for b in ("green", "amber", "red"):
            r = auth.get(f"{BASE_URL}/api/orders", params={"bucket": b, "status": "all", "limit": 200})
            assert r.status_code == 200
            data = r.json()
            # Every item in this filtered response has bucket == b
            for o in data["items"]:
                assert o["bucket"] == b
            # Summary count for this bucket must match the total (across the company, uncapped by page but capped by 1000 backend fetch)
            assert summary[b] == data["total"], (
                f"summary.{b}={summary[b]} but ?bucket={b} returned total={data['total']}"
            )

    def test_bucket_logic_manual_verify(self, auth):
        """Verify per-order bucket logic matches spec:
        exported => done
        processing or no line_items => pending
        validated OR (0 reviews and >=90%) => green
        >=60% => amber
        else => red
        """
        r = auth.get(f"{BASE_URL}/api/orders", params={"status": "all", "limit": 200})
        items = r.json()["items"]
        for o in items:
            status = o.get("status")
            li = o.get("line_items") or []
            pct = o["reliability"]
            review = o["review_count"]
            bucket = o["bucket"]

            if status == "processing" or not li:
                assert bucket == "pending", f"order {o['id']} should be pending, got {bucket}"
            elif status == "exported":
                assert bucket == "done", f"order {o['id']} should be done, got {bucket}"
            elif status == "validated" or (review == 0 and pct >= 90):
                assert bucket == "green", f"order {o['id']} should be green (status={status} rev={review} pct={pct}), got {bucket}"
            elif pct >= 60:
                assert bucket == "amber", f"order {o['id']} should be amber (pct={pct}), got {bucket}"
            else:
                assert bucket == "red", f"order {o['id']} should be red (pct={pct}), got {bucket}"

    def test_bucket_combined_with_status_filter(self, auth):
        # status=all + bucket=amber should return only amber
        r = auth.get(f"{BASE_URL}/api/orders", params={"bucket": "amber", "status": "all"})
        assert r.status_code == 200
        for o in r.json()["items"]:
            assert o["bucket"] == "amber"

    def test_search_q_combines_with_bucket(self, auth):
        # Just verify param combination doesn't error
        r = auth.get(f"{BASE_URL}/api/orders", params={"bucket": "green", "q": "z", "status": "all"})
        assert r.status_code == 200
        data = r.json()
        for o in data["items"]:
            assert o["bucket"] == "green"
            assert "z" in (o.get("customer_name") or "").lower()

    def test_pagination_still_works(self, auth):
        r = auth.get(f"{BASE_URL}/api/orders", params={"limit": 2, "skip": 0, "status": "all"})
        assert r.status_code == 200
        data = r.json()
        assert data["limit"] == 2
        assert data["skip"] == 0
        assert len(data["items"]) <= 2
