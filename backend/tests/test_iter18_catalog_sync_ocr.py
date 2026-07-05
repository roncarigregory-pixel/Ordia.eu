"""Iteration 18 tests — Catalog ERP sync (conservative merge) + OCR scanned PDF.

Covers:
  - Feature 1: POST /api/bridge/agents -> pairing_code -> POST /api/bridge/pair -> token
    - POST /api/bridge/master-data (X-Bridge-Token) with product entries containing one new
      and one existing product; verify catalog_sync {inserted, updated} and that manual price
      of existing product is NOT overwritten.
  - Feature 1: GET /api/catalog/sync-status shape; PUT /api/catalog/autosync toggle;
    when autosync=false, master-data push does NOT modify catalog.
  - Feature 2: POST /api/orders/extract with scanned PDF -> immediate processing order,
    then poll until completed and verify customer_name/line_items are extracted.

Cleanup fixture removes ALL test-created bridge agents, products (category='Da gestionale'
and sku starts with 'SKU-TEST-'), and unsets `catalog_autosync`, `last_catalog_sync`,
`last_catalog_sync_stats` on the demo company. Restores autosync default (True).
"""

import os
import time
import pytest
import requests

def _load_backend_url() -> str:
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        env_path = "/app/frontend/.env"
        if os.path.exists(env_path):
            with open(env_path) as fh:
                for line in fh:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.split("=", 1)[1].strip()
                        break
    if not url:
        raise RuntimeError("REACT_APP_BACKEND_URL not set and not present in /app/frontend/.env")
    return url.rstrip("/")

BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"

DEMO_EMAIL = "demo@ordia.app"
DEMO_PASSWORD = "demo123"

SCANNED_PDF = "/tmp/scanned_order.pdf"


# ---- Fixtures ----------------------------------------------------------------

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok, f"no token in login response: {r.json()}"
    s.headers.update({"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def paired_agent(session):
    """Create a bridge agent, pair it, return {agent_id, token}."""
    r = session.post(f"{API}/bridge/agents",
                     json={"name": "TEST_iter18_agent", "erp_name": "odoo/18"}, timeout=30)
    assert r.status_code == 200, f"create agent failed: {r.status_code} {r.text}"
    ag = r.json()
    pairing_code = ag["pairing_code"]
    agent_id = ag["id"]

    # Pair (unauthenticated call as the on-prem agent would).
    pair = requests.post(f"{API}/bridge/pair", json={"pairing_code": pairing_code}, timeout=30)
    assert pair.status_code == 200, f"pair failed: {pair.status_code} {pair.text}"
    token = pair.json()["token"]
    return {"agent_id": agent_id, "token": token, "erp_name": "odoo/18"}


@pytest.fixture(scope="module", autouse=True)
def cleanup(session):
    """Session-scoped teardown: remove test artifacts from demo account."""
    yield
    # Re-enable autosync (restore default state)
    try:
        session.put(f"{API}/catalog/autosync", json={"enabled": True}, timeout=15)
    except Exception:
        pass
    # Delete test bridge agents (names start with TEST_)
    try:
        rr = session.get(f"{API}/bridge/agents", timeout=15)
        if rr.status_code == 200:
            for a in rr.json():
                if (a.get("name") or "").startswith("TEST_"):
                    session.delete(f"{API}/bridge/agents/{a['id']}", timeout=15)
    except Exception:
        pass
    # Delete products from ERP sync (category 'Da gestionale' or SKU-TEST prefix).
    try:
        pr = session.get(f"{API}/products", timeout=30)
        if pr.status_code == 200:
            for p in pr.json():
                sku = (p.get("sku") or "")
                cat = (p.get("category") or "")
                if cat == "Da gestionale" or sku.startswith("SKU-TEST-"):
                    session.delete(f"{API}/products/{p['id']}", timeout=15)
    except Exception:
        pass


# ---- Feature 1: Bridge catalog sync ------------------------------------------

class TestCatalogSync:
    """Conservative-merge ERP catalog sync via Bridge master-data."""

    def test_sync_status_initial_shape(self, session):
        r = session.get(f"{API}/catalog/sync-status", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        # Required keys
        for k in ("autosync", "last_sync", "product_count", "erp_product_count",
                  "bridge_connected", "erp_name"):
            assert k in d, f"missing key {k} in {d}"
        assert isinstance(d["product_count"], int)
        assert d["product_count"] > 0, "demo catalog should be seeded with products"

    def test_master_data_conservative_merge(self, session, paired_agent):
        # Pick an existing product from the seeded catalog and remember its price.
        pr = session.get(f"{API}/products", timeout=30)
        assert pr.status_code == 200
        catalog = pr.json()
        assert len(catalog) > 0
        # pick a product that has a name and a nonzero price (manual price)
        existing = None
        for p in catalog:
            if p.get("name") and (p.get("price") or 0) > 0:
                existing = p
                break
        assert existing, "need an existing priced product to test conservative merge"
        original_price = float(existing["price"])
        existing_name = existing["name"]

        # Ensure autosync is ON before the push
        session.put(f"{API}/catalog/autosync", json={"enabled": True}, timeout=15)

        # Push: one new + one matching by name (with a different, higher price)
        entries = [
            {"erp_id": "ERP-NEW-1", "code": "SKU-TEST-NEW1",
             "name": "TEST_iter18_NewProduct", "price": 9.99, "unit": "cassa"},
            {"erp_id": "ERP-EXISTING-1", "code": "",
             "name": existing_name, "price": original_price + 100.0, "unit": existing.get("unit") or "pz"},
        ]
        headers = {"X-Bridge-Token": paired_agent["token"], "Content-Type": "application/json"}
        r = requests.post(f"{API}/bridge/master-data",
                          headers=headers,
                          json={"erp_key": "odoo/18", "kind": "product", "entries": entries},
                          timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        cs = body.get("catalog_sync")
        assert cs is not None, f"no catalog_sync in {body}"
        assert cs["enabled"] is True
        assert cs["inserted"] >= 1, f"expected at least 1 inserted, got {cs}"
        assert cs["updated"] >= 1, f"expected at least 1 updated, got {cs}"

        # Verify new product exists
        pr2 = session.get(f"{API}/products", timeout=30)
        assert pr2.status_code == 200
        catalog2 = pr2.json()
        new_p = next((p for p in catalog2 if p.get("name") == "TEST_iter18_NewProduct"), None)
        assert new_p, "newly inserted ERP product not found in /products"
        assert new_p.get("category") == "Da gestionale", f"new product category should be 'Da gestionale', got {new_p.get('category')}"
        assert float(new_p.get("price") or 0) == 9.99

        # Verify existing product's price was NOT overwritten (conservative merge)
        existing2 = next((p for p in catalog2 if p["id"] == existing["id"]), None)
        assert existing2, "existing product missing after sync"
        assert float(existing2.get("price") or 0) == original_price, (
            f"conservative merge failed: existing price {original_price} -> {existing2.get('price')}")

    def test_autosync_toggle_and_disabled_push(self, session, paired_agent):
        # Turn autosync OFF
        r = session.put(f"{API}/catalog/autosync", json={"enabled": False}, timeout=15)
        assert r.status_code == 200
        assert r.json()["autosync"] is False

        # sync-status reflects it
        s = session.get(f"{API}/catalog/sync-status", timeout=15)
        assert s.status_code == 200
        assert s.json()["autosync"] is False

        # Push another product; should NOT modify catalog
        entries = [{"erp_id": "ERP-NEW-2", "code": "SKU-TEST-NEW2",
                    "name": "TEST_iter18_ShouldNotAppear", "price": 5.55, "unit": "pz"}]
        headers = {"X-Bridge-Token": paired_agent["token"], "Content-Type": "application/json"}
        rr = requests.post(f"{API}/bridge/master-data",
                           headers=headers,
                           json={"erp_key": "odoo/18", "kind": "product", "entries": entries},
                           timeout=30)
        assert rr.status_code == 200, rr.text
        cs = rr.json().get("catalog_sync")
        assert cs is not None
        assert cs["enabled"] is False, f"catalog_sync should be disabled: {cs}"
        assert cs["inserted"] == 0 and cs["updated"] == 0

        pr = session.get(f"{API}/products", timeout=30)
        assert pr.status_code == 200
        assert not any(p.get("name") == "TEST_iter18_ShouldNotAppear" for p in pr.json()), \
            "product should NOT have been added while autosync=false"

        # Turn autosync back ON
        r2 = session.put(f"{API}/catalog/autosync", json={"enabled": True}, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["autosync"] is True


# ---- Feature 2: OCR scanned PDF ---------------------------------------------

class TestOCRScannedPDF:
    """POST /orders/extract with scanned PDF returns processing order then completes."""

    def test_scanned_pdf_extract_and_poll(self, session):
        assert os.path.exists(SCANNED_PDF), f"missing {SCANNED_PDF}"

        # Multipart form, so we need to drop the JSON content-type header
        headers = {k: v for k, v in session.headers.items() if k.lower() != "content-type"}
        with open(SCANNED_PDF, "rb") as fh:
            files = {"file": ("scanned_order.pdf", fh, "application/pdf")}
            data = {"source_type": "file"}
            r = requests.post(f"{API}/orders/extract",
                              headers=headers, files=files, data=data, timeout=60)
        assert r.status_code == 200, f"extract failed: {r.status_code} {r.text}"
        order = r.json()
        assert order.get("status") == "processing", f"expected processing status, got {order.get('status')}"
        assert order.get("id"), "no id in returned order"
        order_id = order["id"]

        # Poll up to 90 seconds for the background OCR + extract to finish
        deadline = time.time() + 90
        final = None
        while time.time() < deadline:
            gr = session.get(f"{API}/orders/{order_id}", timeout=30)
            assert gr.status_code == 200, gr.text
            final = gr.json()
            if final.get("status") != "processing":
                break
            time.sleep(3)

        assert final is not None, "no final order retrieved"
        assert final.get("status") != "processing", (
            f"OCR timed out; still processing after 90s: {final.get('status')}")
        assert final.get("status") != "error", f"OCR failed: {final.get('error_message')}"

        # Assertions on the extracted content
        cn = (final.get("customer_name") or "").lower()
        assert "mario" in cn or "ristorante" in cn or "da mario" in cn, (
            f"expected customer 'Ristorante Da Mario', got '{final.get('customer_name')}'")
        items = final.get("line_items") or []
        assert len(items) > 0, "expected non-empty line_items after OCR"

        # Cleanup: delete this order
        try:
            session.delete(f"{API}/orders/{order_id}", timeout=15)
        except Exception:
            pass
