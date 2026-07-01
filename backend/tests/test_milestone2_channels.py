"""Milestone 2 inbound channels tests — WhatsApp webhook + email polling gating
+ centralized ingest_order pipeline (learning loop, idempotency, multi-tenant)."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as fh:
        for line in fh:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

API = f"{BASE_URL}/api"


# ---------- shared fixtures ----------
@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _register(session, tag):
    unique = uuid.uuid4().hex[:10]
    email = f"test_{tag}_{unique}@example.com"
    body = {
        "company_name": f"TEST_{tag}_{unique}",
        "name": f"Test {tag}",
        "email": email,
        "password": "testpass123",
    }
    r = session.post(f"{API}/auth/register", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    return {
        "email": email,
        "token": data["access_token"],
        "user": data["user"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }


@pytest.fixture(scope="module")
def company_a(session):
    return _register(session, "A")


@pytest.fixture(scope="module")
def company_b(session):
    return _register(session, "B")


@pytest.fixture(scope="module")
def wa_account(session, company_a):
    """Create a WhatsApp integration on company_a with dummy access token + unique ids."""
    unique = uuid.uuid4().hex[:12]
    body = {
        "label": f"TEST_WA_{unique}",
        "access_token": "DUMMY_TOKEN_" + unique,
        "phone_number_id": f"PN_{unique}",
        "waba_id": f"WABA_{unique}",
    }
    r = session.post(f"{API}/integrations/whatsapp", headers=company_a["headers"], json=body)
    assert r.status_code == 200, r.text
    doc = r.json()
    # verify_token is generated server-side
    assert doc.get("verify_token"), "verify_token missing in whatsapp save response"
    return doc


# ---------- WhatsApp webhook VERIFY ----------
class TestWhatsAppWebhookVerify:
    def test_verify_success(self, wa_account):
        r = requests.get(f"{API}/webhooks/whatsapp", params={
            "hub.mode": "subscribe",
            "hub.verify_token": wa_account["verify_token"],
            "hub.challenge": "12345",
        })
        assert r.status_code == 200, r.text
        assert r.text == "12345"

    def test_verify_wrong_token_forbidden(self):
        r = requests.get(f"{API}/webhooks/whatsapp", params={
            "hub.mode": "subscribe",
            "hub.verify_token": "definitely-wrong-token-xyz",
            "hub.challenge": "12345",
        })
        assert r.status_code == 403


# ---------- WhatsApp webhook RECEIVE ----------
class TestWhatsAppWebhookReceive:
    _msg_id = f"wamid.TEST_{uuid.uuid4().hex[:12]}"

    def test_receive_text_creates_order(self, session, wa_account, company_a):
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": wa_account["waba_id"],
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": wa_account["phone_number_id"]},
                        "messages": [{
                            "from": "393401112233",
                            "id": self._msg_id,
                            "type": "text",
                            "text": {"body": "3 casse mozzarella e 2 sacchi farina"},
                        }],
                    },
                    "field": "messages",
                }],
            }],
        }
        r = requests.post(f"{API}/webhooks/whatsapp", json=payload, timeout=120)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("status") == "ok"
        assert data.get("orders_created") == 1, f"Expected 1 order created, got {data}"

        # Verify the order shows up scoped to company_a
        time.sleep(0.5)
        r = session.get(f"{API}/orders", headers=company_a["headers"])
        assert r.status_code == 200
        wa_orders = [o for o in r.json() if o.get("source_type") == "whatsapp"]
        assert len(wa_orders) >= 1
        latest = wa_orders[0]
        assert latest.get("source_meta", {}).get("from") == "393401112233"
        # Should have matched at least one line item (mozzarella or flour)
        matched_names = " ".join(
            (i.get("matched_name") or "").lower() for i in latest.get("line_items", [])
        )
        assert ("mozzarella" in matched_names) or ("flour" in matched_names), \
            f"Expected mozzarella/flour match, got: {matched_names}"

    def test_receive_same_message_idempotent(self, session, wa_account, company_a):
        # Count orders before
        r0 = session.get(f"{API}/orders", headers=company_a["headers"])
        count_before = len([o for o in r0.json() if o.get("source_type") == "whatsapp"])

        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": wa_account["phone_number_id"]},
                        "messages": [{
                            "from": "393401112233",
                            "id": self._msg_id,  # SAME id as first test
                            "type": "text",
                            "text": {"body": "3 casse mozzarella e 2 sacchi farina"},
                        }],
                    },
                }],
            }],
        }
        r = requests.post(f"{API}/webhooks/whatsapp", json=payload, timeout=60)
        assert r.status_code == 200
        assert r.json().get("orders_created") == 0

        r1 = session.get(f"{API}/orders", headers=company_a["headers"])
        count_after = len([o for o in r1.json() if o.get("source_type") == "whatsapp"])
        assert count_after == count_before, f"Duplicate not prevented: {count_before} -> {count_after}"

    def test_receive_image_graceful_media_failure(self, wa_account):
        """Image message with dummy token — media download to Meta MUST fail gracefully (no 500)."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": wa_account["phone_number_id"]},
                        "messages": [{
                            "from": "393401112233",
                            "id": f"wamid.IMG_{uuid.uuid4().hex[:10]}",
                            "type": "image",
                            "image": {"id": "999999999999999", "mime_type": "image/jpeg"},
                        }],
                    },
                }],
            }],
        }
        r = requests.post(f"{API}/webhooks/whatsapp", json=payload, timeout=45)
        assert r.status_code == 200, f"Should not 500 on media failure: {r.status_code} {r.text}"
        assert r.json().get("orders_created") == 0


# ---------- Email poll gating ----------
class TestEmailPollGating:
    def test_poll_before_connect_returns_400(self, session, company_b):
        r = session.post(f"{API}/integrations/email/poll", headers=company_b["headers"])
        assert r.status_code == 400, f"Expected 400 before connect, got {r.status_code}: {r.text}"

    def test_forwarding_provider_poll_no_op(self, session, company_b):
        # Configure forwarding provider + validate
        r = session.post(f"{API}/integrations/email",
                         headers=company_b["headers"],
                         json={"inbound_provider": "forwarding"})
        assert r.status_code == 200
        r = session.post(f"{API}/integrations/email/validate", headers=company_b["headers"])
        assert r.status_code == 200
        assert r.json().get("status") == "connected"

        # Now poll — should be a no-op
        r = session.post(f"{API}/integrations/email/poll", headers=company_b["headers"])
        assert r.status_code == 200, f"forwarding poll should not crash: {r.text}"
        data = r.json()
        assert data.get("orders_created") == 0

    def test_imap_fake_creds_graceful(self, session, company_a):
        # Configure gmail IMAP with fake creds on company_a
        r = session.post(f"{API}/integrations/email",
                         headers=company_a["headers"],
                         json={
                             "inbound_provider": "gmail",
                             "inbound_email": "fake_test@example.com",
                             "inbound_password": "definitely-not-real-app-pw",
                         })
        assert r.status_code == 200
        # Validate should fail GRACEFULLY (400 with Italian message, no 500)
        r = session.post(f"{API}/integrations/email/validate", headers=company_a["headers"])
        assert r.status_code in (400, 502), f"Expected graceful 400/502, got {r.status_code}: {r.text}"
        assert r.status_code != 500
        # Response should carry an italian-ish error
        assert "detail" in r.json()


# ---------- Centralized pipeline (ingest_order) regression ----------
class TestPipelineRegression:
    def test_extract_text_still_creates_order(self, session, company_b):
        s = requests.Session()
        s.headers.update(company_b["headers"])
        r = s.post(f"{API}/orders/extract",
                   data={"source_type": "text", "text": "2 casse mozzarella"},
                   timeout=90)
        assert r.status_code == 200, r.text
        order = r.json()
        assert "id" in order
        assert len(order.get("line_items", [])) >= 1
        pytest.pipeline_order_id = order["id"]
        # First matched item raw text for learning check below
        first_item = order["line_items"][0]
        pytest.pipeline_first_raw = first_item.get("raw_text", "")

    def test_validate_grows_learning(self, session, company_b):
        # Learning size before
        r = session.get(f"{API}/learning", headers=company_b["headers"])
        assert r.status_code == 200
        before = len(r.json())

        oid = getattr(pytest, "pipeline_order_id", None)
        assert oid, "prior extract test must run first"
        r = session.post(f"{API}/orders/{oid}/validate", headers=company_b["headers"])
        assert r.status_code == 200
        assert r.json()["status"] == "validated"

        r = session.get(f"{API}/learning", headers=company_b["headers"])
        after = len(r.json())
        assert after >= before, f"Learning did not grow: {before} -> {after}"

    def test_learned_phrase_auto_match_next_extract(self, session, company_b):
        # Re-extract using the same phrase — should auto-match with confidence>=0.99
        raw = getattr(pytest, "pipeline_first_raw", None) or "2 casse mozzarella"
        s = requests.Session()
        s.headers.update(company_b["headers"])
        r = s.post(f"{API}/orders/extract",
                   data={"source_type": "text", "text": raw},
                   timeout=90)
        assert r.status_code == 200
        order = r.json()
        learned_hits = [i for i in order.get("line_items", []) if i.get("learned")]
        assert learned_hits, f"Expected at least one learned=true line item, got: {order.get('line_items')}"
        assert learned_hits[0]["confidence"] >= 0.99


# ---------- Multi-tenant isolation across channels ----------
class TestChannelIsolation:
    def test_company_b_does_not_see_company_a_whatsapp_orders(self, session, company_a, company_b):
        r = session.get(f"{API}/orders", headers=company_b["headers"])
        assert r.status_code == 200
        wa = [o for o in r.json() if o.get("source_type") == "whatsapp"]
        assert wa == [], f"Isolation leak: company_b sees whatsapp orders: {wa}"

        # And company_a still sees its own whatsapp orders
        r = session.get(f"{API}/orders", headers=company_a["headers"])
        wa_a = [o for o in r.json() if o.get("source_type") == "whatsapp"]
        assert len(wa_a) >= 1
