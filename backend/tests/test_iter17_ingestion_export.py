"""
Iteration 17 — Ingestion pipeline (text/PDF/Excel/image/audio) + ERP export end-to-end.
Uses the demo account demo@ordia.app / demo123 which has a seeded catalog of ~25 products.
All AI calls (Claude for extraction, Whisper for audio) are REAL (Emergent LLM key).
"""
import io
import os
import base64
import asyncio
import pytest
import requests
from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from openpyxl import Workbook

def _load_frontend_env():
    p = "/app/frontend/.env"
    if os.path.exists(p):
        with open(p) as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("REACT_APP_BACKEND_URL not found")

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _load_frontend_env()).rstrip("/") + "/api"
DEMO_EMAIL = "demo@ordia.app"
DEMO_PASSWORD = "demo123"

# Track order IDs to cleanup at end
_created_orders: list[str] = []


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/auth/login",
               json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok, f"no token: {r.text}"
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="session")
def catalog(session):
    r = session.get(f"{BASE_URL}/products?limit=100", timeout=15)
    assert r.status_code == 200
    data = r.json()
    items = data.get("items") if isinstance(data, dict) else data
    assert items and len(items) >= 5, f"seed catalog missing: {data}"
    return items


# ---------- Helpers ----------
def _extract(session, form: dict, files=None):
    r = session.post(f"{BASE_URL}/orders/extract", data=form, files=files, timeout=180)
    return r


def _register_order(r):
    assert r.status_code == 200, f"extract failed: {r.status_code} {r.text[:400]}"
    order = r.json()
    assert "id" in order
    _created_orders.append(order["id"])
    return order


def _build_pdf() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 800
    for line in [
        "Ordine per: Trattoria Sole",
        "Consegna: giovedi",
        "",
        "10 casse di pomodori pelati",
        "5 kg mozzarella",
        "3 confezioni di olio extravergine di oliva",
        "2 sacchi farina 00",
    ]:
        c.drawString(72, y, line)
        y -= 20
    c.showPage()
    c.save()
    return buf.getvalue()


def _build_xlsx() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Ordine"
    ws.append(["Prodotto", "Quantita", "Unita"])
    ws.append(["Pomodori pelati", 10, "casse"])
    ws.append(["Mozzarella", 5, "kg"])
    ws.append(["Olio extravergine", 3, "confezioni"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _build_image_order() -> bytes:
    """Render an order note as a PNG (simulates screenshot of a written order)."""
    img = Image.new("RGB", (800, 500), "white")
    d = ImageDraw.Draw(img)
    lines = [
        "Ordine — Bar Roma",
        "Consegna: domani",
        "",
        "10 casse pomodori pelati",
        "5 kg mozzarella",
        "3 confezioni olio evo",
    ]
    y = 30
    for line in lines:
        d.text((30, y), line, fill="black")
        y += 40
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _build_audio() -> bytes:
    """Synthesize an Italian order via edge-tts (MP3)."""
    import edge_tts

    async def gen():
        text = ("Buongiorno, per domani mandami dieci casse di pomodori pelati, "
                "cinque chili di mozzarella e tre confezioni di olio extravergine di oliva. Grazie!")
        communicate = edge_tts.Communicate(text, voice="it-IT-DiegoNeural")
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        return buf.getvalue()

    return asyncio.get_event_loop().run_until_complete(gen()) if False else asyncio.run(gen())


# ---------- Tests: TEXT import ----------
class TestTextImport:
    def test_text_whatsapp_style(self, session, catalog):
        body = ("Buongiorno, per domani: 10 casse di pomodori pelati, "
                "5 kg mozzarella, 3 confezioni di olio evo. Grazie — Trattoria Sole")
        r = _extract(session, {"source_type": "text", "text": body})
        order = _register_order(r)
        assert order["source_type"] == "text"
        lines = order.get("line_items", [])
        assert len(lines) >= 3, f"expected >=3 lines, got {len(lines)}: {lines}"
        # customer_name extraction
        cust = (order.get("customer_name") or "").lower()
        assert "sole" in cust or "trattoria" in cust, f"customer not extracted: {cust!r}"
        # Persist check — GET the order back
        g = session.get(f"{BASE_URL}/orders/{order['id']}", timeout=15)
        assert g.status_code == 200
        assert g.json()["id"] == order["id"]
        assert len(g.json()["line_items"]) == len(lines)


# ---------- Tests: PDF import ----------
class TestPdfImport:
    def test_pdf_upload(self, session, catalog):
        pdf_bytes = _build_pdf()
        files = {"file": ("order.pdf", pdf_bytes, "application/pdf")}
        r = _extract(session, {"source_type": "file"}, files=files)
        order = _register_order(r)
        assert order["source_type"] == "file"
        lines = order["line_items"]
        assert len(lines) >= 3, f"pdf lines: {lines}"


# ---------- Tests: Excel import ----------
class TestExcelImport:
    def test_xlsx_upload(self, session, catalog):
        xlsx_bytes = _build_xlsx()
        files = {"file": ("order.xlsx", xlsx_bytes,
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        r = _extract(session, {"source_type": "file"}, files=files)
        order = _register_order(r)
        lines = order["line_items"]
        assert len(lines) >= 3, f"xlsx lines: {lines}"


# ---------- Tests: Image import ----------
class TestImageImport:
    def test_png_upload(self, session, catalog):
        img_bytes = _build_image_order()
        files = {"file": ("order.png", img_bytes, "image/png")}
        r = _extract(session, {"source_type": "file"}, files=files)
        order = _register_order(r)
        lines = order["line_items"]
        assert len(lines) >= 1, f"image lines: {lines}"


# ---------- Tests: Audio import ----------
class TestAudioImport:
    def test_mp3_upload(self, session, catalog):
        try:
            audio_bytes = _build_audio()
        except Exception as e:
            pytest.skip(f"edge-tts synth failed: {e}")
        assert len(audio_bytes) > 1000, f"audio too small: {len(audio_bytes)}"
        files = {"file": ("order.mp3", audio_bytes, "audio/mpeg")}
        r = _extract(session, {"source_type": "file"}, files=files)
        order = _register_order(r)
        lines = order["line_items"]
        assert len(lines) >= 1, f"audio lines: {lines}"
        # Whisper should have produced a transcript in source_preview
        prev = (order.get("source_preview") or "").lower()
        assert "pomodor" in prev or "mozzarella" in prev or "olio" in prev, \
            f"transcript looks empty: {prev[:200]}"


# ---------- Tests: Order Review edit + save ----------
class TestOrderReviewPersistence:
    def test_edit_line_item_persists(self, session, catalog):
        # create an order first via text
        r = _extract(session, {"source_type": "text",
                               "text": "3 casse mozzarella, 2 kg farina 00"})
        order = _register_order(r)
        oid = order["id"]

        # Modify: bump first line's quantity and add a note
        line_items = order["line_items"]
        assert line_items
        line_items[0]["quantity"] = float(line_items[0].get("quantity", 1)) + 7
        payload = {"line_items": line_items, "notes": "TEST_updated_by_iter17"}
        u = session.put(f"{BASE_URL}/orders/{oid}", json=payload, timeout=30)
        assert u.status_code == 200, u.text
        # Reload and verify persistence
        g = session.get(f"{BASE_URL}/orders/{oid}", timeout=15)
        assert g.status_code == 200
        got = g.json()
        assert got["notes"] == "TEST_updated_by_iter17"
        assert float(got["line_items"][0]["quantity"]) == float(line_items[0]["quantity"])


# ---------- Tests: Approve + Export ----------
class TestApproveAndExport:
    def test_validate_and_export_json_csv_xlsx_pdf(self, session, catalog):
        r = _extract(session, {"source_type": "text",
                               "text": "TEST_iter17 export target: 4 casse mozzarella, 2 kg farina"})
        order = _register_order(r)
        oid = order["id"]

        # Approve
        v = session.post(f"{BASE_URL}/orders/{oid}/validate", timeout=30)
        assert v.status_code == 200, v.text
        assert v.json()["status"] == "validated"

        # Export in all built-in formats
        for fmt, ctype_prefix in [
            ("json", "application/json"),
            ("csv", "text/csv"),
            ("xlsx", "application/vnd.openxmlformats"),
            ("pdf", "application/pdf"),
        ]:
            e = session.get(f"{BASE_URL}/orders/{oid}/export?format={fmt}", timeout=30)
            assert e.status_code == 200, f"{fmt} export: {e.status_code} {e.text[:300]}"
            assert e.headers.get("content-type", "").startswith(ctype_prefix), \
                f"{fmt}: unexpected content-type {e.headers.get('content-type')}"
            assert len(e.content) > 20, f"{fmt}: empty body"

    def test_export_profile_lifecycle(self, session, catalog):
        # Create profile
        prof_body = {
            "name": "TEST_iter17_profile",
            "erp_name": "TestERP",
            "format": "csv",
            "delimiter": ";",
            "decimal_separator": ",",
            "encoding": "UTF-8",
            "has_header": True,
            "columns": [
                {"header": "SKU", "source": "sku"},
                {"header": "Prodotto", "source": "product"},
                {"header": "Q", "source": "quantity"},
                {"header": "UM", "source": "unit"},
                {"header": "Prezzo", "source": "unit_price"},
            ],
        }
        c = session.post(f"{BASE_URL}/export-profiles", json=prof_body, timeout=15)
        assert c.status_code == 200, c.text
        prof = c.json()
        assert prof["name"] == "TEST_iter17_profile"
        pid = prof["id"]

        # Make an order and validate
        r = _extract(session, {"source_type": "text",
                               "text": "TEST_iter17 profile: 2 casse mozzarella"})
        order = _register_order(r)
        oid = order["id"]
        v = session.post(f"{BASE_URL}/orders/{oid}/validate", timeout=30)
        assert v.status_code == 200

        # Export with profile
        e = session.get(f"{BASE_URL}/orders/{oid}/export-profile/{pid}", timeout=30)
        assert e.status_code == 200, e.text
        assert e.headers.get("content-type", "").startswith("text/csv")
        txt = e.content.decode("utf-8", errors="ignore")
        assert "SKU;Prodotto;Q;UM;Prezzo" in txt.splitlines()[0], f"bad header: {txt[:200]}"

        # List includes profile
        lst = session.get(f"{BASE_URL}/export-profiles", timeout=15)
        assert lst.status_code == 200
        assert any(p["id"] == pid for p in lst.json())

        # Delete profile
        d = session.delete(f"{BASE_URL}/export-profiles/{pid}", timeout=15)
        assert d.status_code == 200


# ---------- Session teardown: cleanup orders ----------
@pytest.fixture(scope="session", autouse=True)
def _cleanup(session):
    yield
    for oid in _created_orders:
        try:
            session.delete(f"{BASE_URL}/orders/{oid}", timeout=10)
        except Exception:
            pass
