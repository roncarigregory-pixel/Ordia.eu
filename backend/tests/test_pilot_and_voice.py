"""Focused tests for iteration_2 features:
   - PILOT MODE demo workspace seed (dashboard/stats, orders)
   - VOICE messages (audio -> Whisper -> Claude extraction)
"""
import os
import subprocess
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") \
    else "https://intelligent-orders-1.preview.emergentagent.com"

DEMO_EMAIL = "demo@ordia.app"
DEMO_PASSWORD = "demo123"

EXPECTED_CUSTOMERS = {
    "Trattoria Sole", "Hotel Aurora", "Bar Centrale",
    "Ristorante Da Marco", "Pizzeria Vesuvio",
}
EXPECTED_STATUSES = {"validated", "exported", "needs_review", "ready"}


@pytest.fixture(scope="module")
def demo_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Demo login failed: {r.status_code} {r.text}"
    tok = r.json().get("access_token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def demo_headers(demo_token):
    return {"Authorization": f"Bearer {demo_token}"}


# --------------------------- PILOT / DEMO SEED ---------------------------
class TestDemoSeed:
    def test_dashboard_stats_has_seeded_orders(self, demo_headers):
        r = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=demo_headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total_orders"] >= 5, f"expected >=5 seeded orders, got {data['total_orders']}"
        recent_names = {o.get("customer_name") for o in data.get("recent", [])}
        # At least 3 of the 5 known demo customers should appear in the recent list
        overlap = EXPECTED_CUSTOMERS & recent_names
        assert len(overlap) >= 3, f"expected >=3 demo customer names in recent, got {recent_names}"
        assert isinstance(data.get("hours_saved"), (int, float))
        assert data.get("products", 0) > 0

    def test_orders_list_has_multiple_statuses(self, demo_headers):
        r = requests.get(f"{BASE_URL}/api/orders", headers=demo_headers, timeout=15)
        assert r.status_code == 200, r.text
        orders = r.json()
        assert len(orders) >= 5
        statuses = {o["status"] for o in orders}
        overlap = EXPECTED_STATUSES & statuses
        assert len(overlap) >= 3, f"expected diverse statuses, got {statuses}"


# --------------------------- VOICE EXTRACTION ---------------------------
@pytest.fixture(scope="module")
def italian_voice_wav(tmp_path_factory):
    wav = tmp_path_factory.mktemp("audio") / "order.wav"
    subprocess.run(
        ["espeak-ng", "-v", "it", "-s", "145", "-w", str(wav),
         "tre casse di mozzarella due sacchi di farina una cassa di coca cola"],
        check=True,
    )
    assert wav.exists() and wav.stat().st_size > 1000
    return str(wav)


class TestVoiceExtraction:
    def test_extract_from_audio_wav(self, demo_headers, italian_voice_wav):
        with open(italian_voice_wav, "rb") as f:
            files = {"file": ("order.wav", f, "audio/wav")}
            data = {"source_type": "file"}
            r = requests.post(
                f"{BASE_URL}/api/orders/extract",
                headers=demo_headers, files=files, data=data, timeout=180,
            )
        assert r.status_code == 200, f"{r.status_code} {r.text[:500]}"
        order = r.json()
        # Source preview must indicate voice transcription
        assert isinstance(order.get("source_preview"), str)
        assert order["source_preview"].startswith("[Messaggio vocale trascritto]"), \
            f"unexpected source_preview: {order['source_preview'][:200]}"
        # Must have line items (Whisper transcript + Claude extraction)
        line_items = order.get("line_items") or []
        assert len(line_items) >= 1, "no line items extracted from voice message"

        # Check catalog matching for at least one expected product name
        names = " ".join((li.get("matched_name") or "") for li in line_items).lower()
        expected_hits = ["mozzarella", "flour", "farina", "cola"]
        assert any(k in names for k in expected_hits), \
            f"none of {expected_hits} matched. matched_names={[li.get('matched_name') for li in line_items]}"

        # Persistence check: order retrievable via GET
        oid = order["id"]
        g = requests.get(f"{BASE_URL}/api/orders/{oid}", headers=demo_headers, timeout=15)
        assert g.status_code == 200
        assert g.json()["id"] == oid
        assert g.json()["source_preview"].startswith("[Messaggio vocale trascritto]")
