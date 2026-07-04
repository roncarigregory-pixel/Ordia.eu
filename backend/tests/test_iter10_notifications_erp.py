"""Iteration 10 — Notification Center + ERP connector platform backend tests.

Covers:
- POST /api/orders/extract triggers notification generation (unrecognized_products,
  unknown_customer, low_confidence/order_blocked)
- GET /api/notifications with filters (status, type, q)
- GET /api/notifications/counts shape
- PATCH /api/notifications/{id} (status=resolved, assigned_to)
- ERP connectors listing (6 types)
- ERP connections CRUD, test, sync-order, jobs listing, retry
- Order-never-lost: confirming an order enqueues an export job and resolves related
  notifications; order remains in DB regardless of export outcome
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
API = f"{BASE_URL}/api"

DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "demo@ordia.app")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo123")
HTTPBIN = "https://httpbin.org/post"


# ----------------------------- fixtures --------------------------------------
@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture(scope="session")
def client(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def me(client):
    r = client.get(f"{API}/auth/me", timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


# ----------------------------- helpers ---------------------------------------
def _extract_order(token, text):
    """orders/extract expects multipart form-data."""
    r = requests.post(
        f"{API}/orders/extract",
        headers={"Authorization": f"Bearer {token}"},
        data={"source_type": "text", "text": text},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    return r.json()


# ============================ Notifications =================================
class TestNotifications:
    order_id = None
    created_notif_ids = []
    customer_name = None

    def test_extract_generates_notifications(self, token):
        # Unique customer name per run so `unknown_customer` reliably fires
        TestNotifications.customer_name = f"TESTCUST Iter10 {int(time.time())}"
        text = (
            f"Cliente: {TestNotifications.customer_name}\n"
            "- 5 casse di zzz999-prodottoinesistente\n"
            "- 3 kg di altroignoto_qqq111\n"
        )
        order = _extract_order(token, text)
        assert "id" in order
        TestNotifications.order_id = order["id"]

    def test_list_notifications_for_order(self, client):
        assert TestNotifications.order_id, "extract must run first"
        # Give ingest pipeline a moment (should be sync, but safe)
        time.sleep(0.5)
        r = client.get(f"{API}/notifications", params={"status": "open"}, timeout=30)
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list) and len(items) > 0
        related = [n for n in items if n.get("order_id") == TestNotifications.order_id]
        assert related, f"No notifications for order {TestNotifications.order_id}"
        types = {n["type"] for n in related}
        # Must contain unrecognized_products (unknown SKU) and unknown_customer
        assert "unrecognized_products" in types, f"expected unrecognized_products, got {types}"
        assert "unknown_customer" in types, f"expected unknown_customer, got {types}"
        assert types & {"low_confidence", "order_blocked"}, f"expected low_confidence/order_blocked, got {types}"
        # Priority meta correct
        for n in related:
            if n["type"] in ("unrecognized_products", "low_confidence", "order_blocked"):
                assert n["priority"] == "high"
            if n["type"] == "unknown_customer":
                assert n["priority"] == "medium"
            assert n["status"] == "open"
            assert n["title"] and n["suggested_action"]
        TestNotifications.created_notif_ids = [n["id"] for n in related]

    def test_counts_shape(self, client):
        r = client.get(f"{API}/notifications/counts", timeout=30)
        assert r.status_code == 200
        data = r.json()
        for k in ("open", "high", "medium", "low"):
            assert k in data and isinstance(data[k], int), data
        assert data["open"] >= 1

    def test_filters_type_and_search(self, client):
        r = client.get(f"{API}/notifications", params={"status": "open", "type": "unrecognized_products"}, timeout=30)
        assert r.status_code == 200
        assert all(n["type"] == "unrecognized_products" for n in r.json())
        # search by customer substring
        r2 = client.get(f"{API}/notifications", params={"q": TestNotifications.customer_name}, timeout=30)
        assert r2.status_code == 200
        assert len(r2.json()) >= 1

    def test_patch_assign_and_resolve(self, client, me):
        assert TestNotifications.created_notif_ids
        nid = TestNotifications.created_notif_ids[0]
        r = client.patch(f"{API}/notifications/{nid}", json={"assigned_to": me["id"]}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["assigned_to"] == me["id"]

        r2 = client.patch(f"{API}/notifications/{nid}", json={"status": "resolved"}, timeout=30)
        assert r2.status_code == 200
        assert r2.json()["status"] == "resolved"

        # verify persistence via GET filtered by open (should not include it)
        r3 = client.get(f"{API}/notifications", params={"status": "open"}, timeout=30)
        assert nid not in {n["id"] for n in r3.json()}

    def test_patch_empty_body_400(self, client):
        assert TestNotifications.created_notif_ids
        nid = TestNotifications.created_notif_ids[-1]
        r = client.patch(f"{API}/notifications/{nid}", json={}, timeout=30)
        assert r.status_code == 400


# ============================ ERP Connectors ================================
class TestErp:
    conn_id = None
    order_id = None
    job_id = None

    def test_list_connectors_returns_six(self, client):
        r = client.get(f"{API}/erp/connectors", timeout=30)
        assert r.status_code == 200
        data = r.json()
        types = {c["type"] for c in data}
        assert types == {"generic", "odoo", "sap", "business_central", "zucchetti", "teamsystem"}, types
        for c in data:
            assert "name" in c and "capabilities" in c and "config_fields" in c

    def test_create_generic_connection_and_mask(self, client):
        payload = {
            "connector_type": "generic",
            "name": "TEST_httpbin_iter10",
            "config": {
                "base_url": HTTPBIN,
                "orders_endpoint": HTTPBIN,
                "auth_header_name": "Authorization",
                "auth_token": "supersecret_token_12345",
            },
            "mappings": {"field_map": {"order_id": "external_ref"}},
            "active": True,
        }
        r = client.post(f"{API}/erp/connections", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        conn = r.json()
        assert conn["connector_type"] == "generic"
        assert conn["active"] is True
        # token must be masked in read
        assert conn["config"]["auth_token"] != "supersecret_token_12345"
        assert "•" in conn["config"]["auth_token"] or "…" in conn["config"]["auth_token"]
        TestErp.conn_id = conn["id"]

    def test_list_connections_contains_new(self, client):
        r = client.get(f"{API}/erp/connections", timeout=30)
        assert r.status_code == 200
        ids = {c["id"] for c in r.json()}
        assert TestErp.conn_id in ids

    def test_connection_test_endpoint(self, client):
        """test does a GET — httpbin/post returns 405 for GET, so 502 is acceptable (no crash)."""
        r = client.post(f"{API}/erp/connections/{TestErp.conn_id}/test", timeout=30)
        assert r.status_code in (200, 502), r.text  # both OK, just no crash

    def test_create_order_for_export(self, token):
        # Use a normal-looking order (may still be needs_review; that's fine for sync-order)
        text = "Cliente: Bar Trattoria Roma\n- 2 casse di pasta\n- 1 kg di pomodori"
        order = _extract_order(token, text)
        TestErp.order_id = order["id"]

    def test_sync_order_success_via_httpbin(self, client):
        assert TestErp.conn_id and TestErp.order_id
        r = client.post(
            f"{API}/erp/connections/{TestErp.conn_id}/sync-order/{TestErp.order_id}",
            timeout=60,
        )
        assert r.status_code == 200, r.text
        job = r.json()
        assert job["status"] == "success", job
        assert job["attempts"] >= 1
        TestErp.job_id = job["id"]

    def test_jobs_listing(self, client):
        r = client.get(f"{API}/erp/jobs", timeout=30)
        assert r.status_code == 200
        ids = {j["id"] for j in r.json()}
        assert TestErp.job_id in ids

    def test_retry_on_error_job(self, client):
        """Create an intentionally-failing connection, sync-order -> error, then retry."""
        bad = {
            "connector_type": "generic",
            "name": "TEST_bad_iter10",
            "config": {
                "base_url": "http://127.0.0.1:1/does-not-exist",
                "orders_endpoint": "http://127.0.0.1:1/does-not-exist",
            },
            "active": False,  # keep our httpbin one active
        }
        r = client.post(f"{API}/erp/connections", json=bad, timeout=30)
        assert r.status_code == 200, r.text
        bad_id = r.json()["id"]
        try:
            r2 = client.post(
                f"{API}/erp/connections/{bad_id}/sync-order/{TestErp.order_id}",
                timeout=30,
            )
            assert r2.status_code == 200
            job = r2.json()
            assert job["status"] == "error", job
            assert job["last_error"]
            # Retry should re-run
            r3 = client.post(f"{API}/erp/jobs/{job['id']}/retry", timeout=30)
            assert r3.status_code == 200
            assert r3.json()["attempts"] >= 2
        finally:
            client.delete(f"{API}/erp/connections/{bad_id}", timeout=30)

    # ------------------ chain: confirm -> job + resolve notifs --------------
    def test_confirm_order_enqueues_export_and_resolves_notifs(self, client, token):
        """Validating an order with an active ERP connection MUST enqueue an export
        job and resolve open notifications for that order. The order stays in DB."""
        # Create a fresh unknown-customer order to guarantee it has open notifications
        text = "Cliente: TESTChainCustomer Iter10\n- 4 casse di pasta\n- 2 kg di pomodori"
        order = _extract_order(token, text)
        oid = order["id"]

        # Get open notifs before
        pre = client.get(f"{API}/notifications", params={"status": "open"}, timeout=30).json()
        pre_related = [n["id"] for n in pre if n.get("order_id") == oid]

        # Validate/confirm
        rv = client.post(f"{API}/orders/{oid}/validate", timeout=60)
        assert rv.status_code == 200, rv.text

        # Order remains in DB
        rg = client.get(f"{API}/orders/{oid}", timeout=30)
        assert rg.status_code == 200
        assert rg.json()["status"] in ("confirmed", "exported", "validated")

        # Export job enqueued
        rj = client.get(f"{API}/erp/jobs", timeout=30).json()
        assert any(j["order_id"] == oid for j in rj), "no export job enqueued after confirm"

        # Related open notifications resolved
        post = client.get(f"{API}/notifications", params={"status": "open"}, timeout=30).json()
        post_related = [n["id"] for n in post if n.get("order_id") == oid]
        assert not post_related or set(post_related).isdisjoint(pre_related), (
            f"open notifs still linger for order {oid}: {post_related}")

    # ----------------------- cleanup ----------------------------------------
    def test_zzz_cleanup_delete_connection(self, client):
        """Delete the httpbin connection so the demo tenant stays clean."""
        assert TestErp.conn_id
        r = client.delete(f"{API}/erp/connections/{TestErp.conn_id}", timeout=30)
        assert r.status_code == 200
        # Verify removed
        r2 = client.get(f"{API}/erp/connections", timeout=30)
        assert TestErp.conn_id not in {c["id"] for c in r2.json()}
