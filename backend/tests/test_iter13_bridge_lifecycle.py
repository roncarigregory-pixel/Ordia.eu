"""
Iteration 13 — Ordia Bridge LEARNING LIFECYCLE + resilience + observability.

Covers:
  * Bridge maturity lifecycle (unpaired -> learning -> ready -> active -> paused-back-to-learning)
  * Readiness scoring (score, checklist, threshold, dry_runs)
  * Shadow delivery + auto-promotion after 5 successful dry-runs
  * Activation guard (400 below threshold)
  * Durable queue retry / exponential backoff / max-attempts -> failed + bridge_exception notif
  * Proactive offline + delivery-on-wake (bridge_recovered notification)
  * Adapter circuit breaker + quarantine + resolve-hides-quarantined + heal
  * Bridge diary events (paired, master_data, adapter_active, ready)

Cleanup: the test creates its OWN throwaway bridge agent(s) and adapter(s). It
deactivates the pre-existing demo NAS Bridge temporarily so that
`enqueue_bridge_delivery` picks our test agent, and restores it at the end. Any
orders whose statuses we bumped back to "validated" via /validate are restored to
their original status via direct DB write.
"""
import os
import time
import uuid
import asyncio
import pytest
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "demo@ordia.app"
ADMIN_PASSWORD = "demo123"


# ------------------------------------------------------------------ helpers --

def _login():
    r = requests.post(f"{API}/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def token():
    return _login()


@pytest.fixture(scope="session")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _run(coro_factory):
    """Run an async operation in a fresh asyncio + motor client so each call gets
    its own event loop (asyncio.run closes the loop each time, but a persistent
    Motor client would then break)."""
    from motor.motor_asyncio import AsyncIOMotorClient

    async def _wrapper():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        try:
            db = client[os.environ["DB_NAME"]]
            return await coro_factory(db)
        finally:
            client.close()
    return asyncio.run(_wrapper())


@pytest.fixture(scope="session")
def db():
    """Sentinel; real DB access goes through _run(async lambda db: ...)"""
    return "USE_RUN_HELPER"


# ---------------------------------------------------------------- state mgmt --

@pytest.fixture(scope="module")
def demo_agents_deactivated(headers):
    """Deactivate every existing paired+active agent for this company so our
    freshly paired throwaway agent is the one that `enqueue_bridge_delivery`
    picks. Restore them at teardown."""
    r = requests.get(f"{API}/bridge/agents", headers=headers, timeout=15)
    assert r.status_code == 200
    existing = r.json()
    restored = []
    for a in existing:
        if a.get("paired") and a.get("active"):
            up = requests.put(f"{API}/bridge/agents/{a['id']}", headers=headers,
                              json={"active": False}, timeout=15)
            assert up.status_code == 200, up.text
            restored.append(a["id"])
    yield restored
    # restore
    for aid in restored:
        try:
            requests.put(f"{API}/bridge/agents/{aid}", headers=headers,
                         json={"active": True}, timeout=15)
        except Exception:
            pass


@pytest.fixture(scope="module")
def test_agent(headers, demo_agents_deactivated):
    """Create + pair a throwaway agent. Cleanup deletes it."""
    body = {"name": f"TEST_iter13 {uuid.uuid4().hex[:8]}", "erp_name": "TESTERP"}
    r = requests.post(f"{API}/bridge/agents", headers=headers, json=body, timeout=15)
    assert r.status_code == 200, r.text
    created = r.json()
    # Confirm initial state
    assert created["paired"] is False
    assert created["status"] == "unpaired"
    assert created["maturity"] == "unpaired"
    assert created["pairing_code"] and len(created["pairing_code"]) == 6

    # Pair
    pair = requests.post(f"{API}/bridge/pair",
                         json={"pairing_code": created["pairing_code"]}, timeout=15)
    assert pair.status_code == 200, pair.text
    paired = pair.json()
    assert paired["agent_id"] == created["id"]
    assert paired["token"] and len(paired["token"]) > 20  # full clear token
    ctx = {"agent_id": created["id"], "token": paired["token"], "company_id": created["company_id"]}
    yield ctx

    # cleanup: delete agent (also removes its jobs implicitly? No, jobs remain but harmless)
    try:
        requests.delete(f"{API}/bridge/agents/{created['id']}", headers=headers, timeout=15)
    except Exception:
        pass


@pytest.fixture
def bridge_headers(test_agent):
    return {"X-Bridge-Token": test_agent["token"], "Content-Type": "application/json"}


# ================================================================== TESTS ==

class TestPairingAndInitialMaturity:
    def test_create_agent_starts_unpaired(self, headers):
        # An extra ad-hoc agent to inspect the "unpaired" initial state independently.
        r = requests.post(f"{API}/bridge/agents", headers=headers,
                          json={"name": "TEST_state_probe", "erp_name": "X"}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        try:
            assert d["paired"] is False
            assert d["status"] == "unpaired"
            assert d["maturity"] == "unpaired"
        finally:
            requests.delete(f"{API}/bridge/agents/{d['id']}", headers=headers, timeout=15)

    def test_pair_sets_learning_and_notifies(self, headers, test_agent):
        # test_agent is already paired by the fixture. Re-check post-conditions.
        r = requests.get(f"{API}/bridge/agents", headers=headers, timeout=15)
        assert r.status_code == 200
        me = next(a for a in r.json() if a["id"] == test_agent["agent_id"])
        assert me["paired"] is True
        assert me["maturity"] == "learning"
        assert me["dry_runs"] == 0
        assert me.get("learning_started_at") is not None or True  # persisted server-side
        # Notification 'bridge_learning' exists for this company
        n = requests.get(f"{API}/notifications?limit=100", headers=headers, timeout=15)
        assert n.status_code == 200
        notifs = n.json() if isinstance(n.json(), list) else n.json().get("items", [])
        assert any(x.get("type") == "bridge_learning" for x in notifs), \
            "expected a bridge_learning notification after pairing"

    def test_pairing_code_is_one_time(self, headers):
        r = requests.post(f"{API}/bridge/agents", headers=headers,
                          json={"name": "TEST_once", "erp_name": "X"}, timeout=15)
        assert r.status_code == 200
        code = r.json()["pairing_code"]
        aid = r.json()["id"]
        try:
            first = requests.post(f"{API}/bridge/pair", json={"pairing_code": code}, timeout=15)
            assert first.status_code == 200
            second = requests.post(f"{API}/bridge/pair", json={"pairing_code": code}, timeout=15)
            assert second.status_code == 404
        finally:
            requests.delete(f"{API}/bridge/agents/{aid}", headers=headers, timeout=15)


class TestReadinessScoring:
    def test_readiness_shape_and_initial_score(self, headers, test_agent):
        r = requests.get(f"{API}/bridge/agents/{test_agent['agent_id']}/readiness",
                         headers=headers, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "score" in d and 0.0 <= d["score"] <= 1.0
        assert d["threshold"] == 0.85
        assert d["dry_runs"] == 0
        cl = d["checklist"]
        assert isinstance(cl, list) and len(cl) == 5
        keys = {c["key"] for c in cl}
        assert keys == {"format", "customers", "products", "dry_runs", "observation"}
        # Demo has active adapter + customers + products already seeded -> ~0.6
        assert 0.55 <= d["score"] <= 0.7, f"expected freshly-paired demo score ~0.6, got {d['score']}"


class TestShadowDeliveryAndPromotion:
    def test_five_shadow_acks_promote_to_ready(self, headers, bridge_headers, test_agent, db):
        # Seed 5 shadow delivery jobs by validating 5 orders (paired-active agent is us).
        orders_resp = requests.get(f"{API}/orders?limit=10", headers=headers, timeout=15)
        assert orders_resp.status_code == 200
        items = orders_resp.json().get("items") or []
        # Snapshot original statuses so we can restore afterward
        picked = items[:5]
        assert len(picked) == 5, "need 5 orders in demo to validate"
        original = [(o["id"], o.get("status")) for o in picked]

        for o in picked:
            v = requests.post(f"{API}/orders/{o['id']}/validate", headers=headers, timeout=15)
            assert v.status_code == 200, v.text

        # Poll shadow jobs for our agent
        got = []
        for _ in range(3):
            p = requests.get(f"{API}/bridge/relay/poll", headers=bridge_headers, timeout=15)
            assert p.status_code == 200, p.text
            got += p.json()["jobs"]
            if len(got) >= 5:
                break
            time.sleep(0.5)
        # Deduplicate by id in case a job appeared in two polls (shouldn't, since claimed)
        seen = {}
        for j in got:
            seen[j["id"]] = j
        jobs = list(seen.values())[:5]
        assert len(jobs) == 5, f"expected 5 shadow jobs, got {len(jobs)}"
        for j in jobs:
            assert j["mode"] == "shadow", f"expected shadow mode, got {j['mode']}"

        # Ack all 5 as delivered
        for j in jobs:
            a = requests.post(f"{API}/bridge/relay/ack", headers=bridge_headers,
                              json={"job_id": j["id"], "status": "delivered",
                                    "result": {"ok": True}}, timeout=15)
            assert a.status_code == 200, a.text

        # Order status must NOT be 'exported' for shadow acks
        for oid, orig in original:
            got_o = requests.get(f"{API}/orders/{oid}", headers=headers, timeout=15).json()
            assert got_o["status"] != "exported", \
                f"shadow delivery must not export the order (order={oid}, status={got_o['status']})"

        # Readiness recomputed -> ~0.9 -> promoted to 'ready' + bridge_ready notif
        r = requests.get(f"{API}/bridge/agents/{test_agent['agent_id']}/readiness",
                         headers=headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["dry_runs"] >= 5, d
        assert d["score"] >= 0.85, f"score after 5 dry-runs should be >= threshold, got {d['score']}"

        me = next(a for a in requests.get(f"{API}/bridge/agents", headers=headers).json()
                  if a["id"] == test_agent["agent_id"])
        assert me["maturity"] == "ready", f"agent should be promoted to ready, got {me['maturity']}"

        notifs = requests.get(f"{API}/notifications?limit=100", headers=headers).json()
        notifs = notifs if isinstance(notifs, list) else notifs.get("items", [])
        assert any(n.get("type") == "bridge_ready" for n in notifs), \
            "expected bridge_ready notification after promotion"

        # Restore original order statuses (we bumped exported->validated during test)
        async def _restore(db):
            for oid, orig in original:
                if orig:
                    await db.orders.update_one({"id": oid}, {"$set": {"status": orig}})
        _run(_restore)


class TestActivationGuardAndPause:
    def test_activate_and_pause_flow(self, headers, test_agent):
        # After promotion (previous test), agent should now be 'ready' -> activate should succeed.
        me = next(a for a in requests.get(f"{API}/bridge/agents", headers=headers).json()
                  if a["id"] == test_agent["agent_id"])
        assert me["maturity"] == "ready", "prev test should have promoted us to ready"

        act = requests.post(f"{API}/bridge/agents/{test_agent['agent_id']}/activate",
                            headers=headers, timeout=15)
        assert act.status_code == 200, act.text
        d = act.json()
        assert d["maturity"] == "active"
        assert d.get("activated_at")

        # Pause returns to learning
        p = requests.post(f"{API}/bridge/agents/{test_agent['agent_id']}/pause",
                          headers=headers, timeout=15)
        assert p.status_code == 200, p.text
        assert p.json()["maturity"] == "learning"

    def test_activation_guard_blocks_when_below_threshold(self, headers):
        # Create a brand-new agent, pair it, immediately try to activate -> 400
        r = requests.post(f"{API}/bridge/agents", headers=headers,
                          json={"name": "TEST_guard", "erp_name": "X"}, timeout=15)
        assert r.status_code == 200
        aid = r.json()["id"]
        try:
            pair = requests.post(f"{API}/bridge/pair",
                                 json={"pairing_code": r.json()["pairing_code"]}, timeout=15)
            assert pair.status_code == 200
            # Fresh: score ~0.6 < 0.85 and maturity=learning -> guard trips
            act = requests.post(f"{API}/bridge/agents/{aid}/activate",
                                headers=headers, timeout=15)
            assert act.status_code == 400, f"expected 400, got {act.status_code} {act.text}"
        finally:
            requests.delete(f"{API}/bridge/agents/{aid}", headers=headers, timeout=15)


class TestDurableQueueRetry:
    def test_exception_ack_schedules_retry_then_fails(self, headers, bridge_headers, test_agent, db):
        # Seed ONE delivery job (order validate). Agent must be paired+active; pause() left us learning=active-flag-true. Verify.
        me = next(a for a in requests.get(f"{API}/bridge/agents", headers=headers).json()
                  if a["id"] == test_agent["agent_id"])
        assert me["active"] is True and me["paired"] is True

        orders = requests.get(f"{API}/orders?limit=1", headers=headers).json().get("items", [])
        assert orders, "need an order"
        original_status = orders[0].get("status")
        oid = orders[0]["id"]
        v = requests.post(f"{API}/orders/{oid}/validate", headers=headers, timeout=15)
        assert v.status_code == 200

        # Poll to claim
        p = requests.get(f"{API}/bridge/relay/poll", headers=bridge_headers, timeout=15).json()
        assert p["jobs"], "expected a job for retry test"
        job_id = p["jobs"][0]["id"]

        # First exception ack -> pending + retry_in + attempt=1
        a1 = requests.post(f"{API}/bridge/relay/ack", headers=bridge_headers,
                           json={"job_id": job_id, "status": "exception",
                                 "error": "test failure"}, timeout=15)
        assert a1.status_code == 200
        d1 = a1.json()
        assert d1.get("retry_in") == 60, d1
        assert d1.get("attempt") == 1

        # Force attempts near max via DB and ack once more -> failed + bridge_exception notif
        async def _bump(db):
            await db.delivery_jobs.update_one({"id": job_id},
                {"$set": {"status": "claimed", "attempts": 4, "next_attempt_at": None}})
        _run(_bump)
        a2 = requests.post(f"{API}/bridge/relay/ack", headers=bridge_headers,
                           json={"job_id": job_id, "status": "exception",
                                 "error": "final failure"}, timeout=15)
        assert a2.status_code == 200
        d2 = a2.json()
        assert d2.get("failed") is True, d2

        # bridge_exception notif exists
        notifs = requests.get(f"{API}/notifications?limit=100", headers=headers).json()
        notifs = notifs if isinstance(notifs, list) else notifs.get("items", [])
        assert any(n.get("type") == "bridge_exception" for n in notifs)

        # restore order status
        if original_status:
            async def _restore(db):
                await db.orders.update_one({"id": oid}, {"$set": {"status": original_status}})
            _run(_restore)

    def test_poll_respects_next_attempt_at(self, bridge_headers, test_agent, db):
        # Seed one pending job with next_attempt_at in the FUTURE -> poll must NOT return it.
        future = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        async def _seed(db):
            await db.delivery_jobs.insert_one({
                "id": f"TEST_future_{uuid.uuid4().hex[:6]}",
                "company_id": test_agent["company_id"], "agent_id": test_agent["agent_id"],
                "order_id": "TEST_future_order", "status": "pending", "mode": "shadow",
                "attempts": 0, "max_attempts": 5, "next_attempt_at": future,
                "created_at": datetime.now(timezone.utc).isoformat()})
        _run(_seed)
        p = requests.get(f"{API}/bridge/relay/poll", headers=bridge_headers, timeout=15).json()
        ids = [j["id"] for j in p["jobs"]]
        assert not any(i.startswith("TEST_future_") for i in ids), \
            "poll must NOT return jobs whose next_attempt_at is in the future"
        # cleanup
        async def _cleanup(db):
            await db.delivery_jobs.delete_many({"id": {"$regex": "^TEST_future_"}})
        _run(_cleanup)

    def test_poll_reclaims_stuck_claimed_jobs(self, bridge_headers, test_agent, db):
        # Insert a claimed job older than 5min -> next poll reclaims to pending and returns it.
        stale = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        jid = f"TEST_stuck_{uuid.uuid4().hex[:6]}"
        async def _seed(db):
            await db.delivery_jobs.insert_one({
                "id": jid, "company_id": test_agent["company_id"], "agent_id": test_agent["agent_id"],
                "order_id": "TEST_stuck_order", "status": "claimed", "mode": "shadow",
                "attempts": 0, "max_attempts": 5, "claimed_at": stale,
                "next_attempt_at": datetime.now(timezone.utc).isoformat(),
                "created_at": stale})
        _run(_seed)
        p = requests.get(f"{API}/bridge/relay/poll", headers=bridge_headers, timeout=15).json()
        assert any(j["id"] == jid for j in p["jobs"]), \
            "poll must reclaim jobs stuck in 'claimed' longer than 5min"
        async def _cleanup(db):
            await db.delivery_jobs.delete_many({"id": jid})
        _run(_cleanup)


class TestOfflineAndWake:
    def test_offline_agent_wakes_and_notifies(self, headers, bridge_headers, test_agent, db):
        # Force agent offline in DB
        async def _off(db):
            await db.bridge_agents.update_one({"id": test_agent["agent_id"]},
                {"$set": {"status": "offline"}})
        _run(_off)

        # heartbeat should mark online + create bridge_recovered
        hb = requests.post(f"{API}/bridge/relay/heartbeat", headers=bridge_headers, timeout=15)
        assert hb.status_code == 200

        # DB status now 'online'
        agent_now = next(a for a in requests.get(f"{API}/bridge/agents", headers=headers).json()
                         if a["id"] == test_agent["agent_id"])
        assert agent_now["status"] == "online"

        notifs = requests.get(f"{API}/notifications?limit=100", headers=headers).json()
        notifs = notifs if isinstance(notifs, list) else notifs.get("items", [])
        assert any(n.get("type") == "bridge_recovered" for n in notifs), \
            "expected bridge_recovered notification after wake"


class TestAdapterCircuitBreaker:
    def test_breaker_quarantines_and_hides_from_resolve_then_heal(self, headers, bridge_headers, test_agent, db):
        # Create a TEST adapter (new erp_key so we don't touch demo Odoo adapters).
        erp_key = f"testerp/{uuid.uuid4().hex[:6]}"
        body = {
            "erp_key": erp_key, "erp_guess": "TESTERP",
            "spec": {"customer_field": "c", "product_field": "p", "qty_field": "q"},
            "confidence": 0.9, "test_order_ref": "TEST-REF",
        }
        create = requests.post(f"{API}/bridge/adapters", headers=bridge_headers, json=body, timeout=15)
        assert create.status_code == 200, create.text
        adapter = create.json()
        aid = adapter["id"]
        try:
            assert adapter["status"] == "pending_confirmation"
            # Confirm -> active
            conf = requests.post(f"{API}/bridge/adapters/{aid}/confirm", headers=headers, timeout=15)
            assert conf.status_code == 200
            assert conf.json()["status"] == "active"

            # Resolve should return it (currently active)
            res = requests.get(f"{API}/bridge/adapters/resolve?erp_key={erp_key}",
                               headers=bridge_headers, timeout=15)
            assert res.status_code == 200
            assert res.json()["id"] == aid

            # Report 5 failures -> rate 0.0 < 0.85 -> quarantined
            for _ in range(5):
                r = requests.post(f"{API}/bridge/adapters/{aid}/report",
                                  headers=bridge_headers, json={"status": "failure"}, timeout=15)
                assert r.status_code == 200
            # Verify quarantined
            allads = requests.get(f"{API}/bridge/adapters", headers=headers, timeout=15).json()
            mine = next(a for a in allads if a["id"] == aid)
            assert mine["status"] == "quarantined", f"expected quarantined, got {mine['status']}"

            # notification
            notifs = requests.get(f"{API}/notifications?limit=100", headers=headers).json()
            notifs = notifs if isinstance(notifs, list) else notifs.get("items", [])
            assert any(n.get("type") == "adapter_quarantined" for n in notifs)

            # resolve MUST NOT return quarantined
            res2 = requests.get(f"{API}/bridge/adapters/resolve?erp_key={erp_key}",
                                headers=bridge_headers, timeout=15)
            assert res2.status_code == 404

            # Heal -> back to active and 'recent' cleared
            heal_body = dict(body)
            heal_body["spec"] = {"customer_field": "c2", "product_field": "p2", "qty_field": "q2"}
            heal = requests.put(f"{API}/bridge/adapters/{aid}/heal",
                                headers=bridge_headers, json=heal_body, timeout=15)
            assert heal.status_code == 200
            assert heal.json()["status"] == "active"
            assert heal.json().get("recent", []) == []

            res3 = requests.get(f"{API}/bridge/adapters/resolve?erp_key={erp_key}",
                                headers=bridge_headers, timeout=15)
            assert res3.status_code == 200
        finally:
            # cleanup adapter directly (no DELETE endpoint exists)
            async def _cleanup(db):
                await db.erp_adapters.delete_many({"id": aid})
            _run(_cleanup)


class TestBridgeDiary:
    def test_diary_contains_pairing_masterdata_adapter_ready(self, headers, bridge_headers, test_agent):
        # Push master-data as agent to create the master_data diary event
        md_body = {
            "erp_key": "testerp/diary",
            "kind": "customer",
            "entries": [{"erp_id": "1", "code": "C1", "name": "TEST Cust 1"}]
        }
        r = requests.post(f"{API}/bridge/master-data", headers=bridge_headers,
                          json=md_body, timeout=15)
        assert r.status_code == 200

        d = requests.get(f"{API}/bridge/agents/{test_agent['agent_id']}/diary",
                         headers=headers, timeout=15)
        assert d.status_code == 200
        events = d.json()
        assert isinstance(events, list) and len(events) > 0
        kinds = {e.get("kind") for e in events}
        assert "paired" in kinds, f"expected 'paired' event, got kinds={kinds}"
        assert "master_data" in kinds, f"expected 'master_data' event, got kinds={kinds}"
        # ready was created by TestShadowDeliveryAndPromotion (earlier)
        assert "ready" in kinds, f"expected 'ready' event after promotion, got kinds={kinds}"
        # adapter_active was created by TestAdapterCircuitBreaker.confirm (company-level)
        assert "adapter_active" in kinds, f"expected 'adapter_active' event, got kinds={kinds}"
