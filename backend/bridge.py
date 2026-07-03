"""Ordia Bridge (modularized) — lifecycle, durable delivery queue, learned ERP
adapters (network effect + circuit breaker), diary and weekly summary.

Wired by server.py via setup_bridge(api, ctx): all shared app primitives (db, auth
deps, helpers, notification/email) are injected through ctx, so this module has NO
import dependency on server.py. Behavior is identical to the previous inline code.
"""
import os
import uuid
import secrets
import base64
import asyncio
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, Field


def setup_bridge(api, ctx):
    db = ctx["db"]
    logger = ctx["logger"]
    now_iso = ctx["now_iso"]
    history_entry = ctx["history_entry"]
    create_notification = ctx["create_notification"]
    standardize_order = ctx["standardize_order"]
    render_with_profile = ctx["render_with_profile"]
    get_current_user = ctx["get_current_user"]
    require_privileged = ctx["require_privileged"]
    mask_secret = ctx["mask_secret"]
    RESEND_API_KEY = ctx["RESEND_API_KEY"]
    SENDER_EMAIL = ctx["SENDER_EMAIL"]
    resend = ctx["resend"]

    # ---- Ordia Bridge: agents, pairing, delivery queue, relay ------------------
    def _gen_pairing_code() -> str:
        return f"{secrets.randbelow(1000000):06d}"

    def _agent_public(a: dict) -> dict:
        a = dict(a)
        if a.get("token"):
            a["token"] = mask_secret(a["token"])
        a.setdefault("maturity", "learning" if a.get("paired") else "unpaired")
        a.setdefault("readiness", 0.0)
        a.setdefault("dry_runs", 0)
        return a

    # ---- Bridge maturity lifecycle: the agent LEARNS before it writes for real ----
    # A freshly paired Bridge starts in "learning" (shadow) mode: approved orders are
    # delivered as test/draft while it learns the ERP format, syncs master-data, and
    # accumulates successful dry-runs. When its readiness score crosses the threshold,
    # it is promoted to "ready" and the operator is notified to activate auto-insertion.
    BRIDGE_DRY_RUN_TARGET = 5      # successful shadow deliveries to fully trust the flow
    BRIDGE_OBS_DAYS = 7           # observation window (a bonus signal, not a hard gate)
    BRIDGE_READY_THRESHOLD = 0.85  # readiness needed to offer auto-insertion

    async def compute_readiness(agent: dict) -> dict:
        """Signal-driven readiness (0..1). Real learning signals dominate; calendar time
        is only a small bonus so a well-fed Bridge can be ready without waiting arbitrarily."""
        company_id = agent["company_id"]
        active_adapter = await db.erp_adapters.find_one({"status": "active"}, {"_id": 0})
        format_known = bool(agent.get("profile_id")) or bool(active_adapter)
        md_kinds = await db.erp_master_data.distinct("kind", {"company_id": company_id})
        has_customers = "customer" in md_kinds
        has_products = "product" in md_kinds
        dry_runs = agent.get("dry_runs", 0) or 0
        dry_ratio = min(dry_runs / BRIDGE_DRY_RUN_TARGET, 1.0)
        started = agent.get("learning_started_at") or agent.get("paired_at")
        days = 0.0
        if started:
            try:
                days = (datetime.now(timezone.utc) - datetime.fromisoformat(started)).total_seconds() / 86400
            except Exception:
                days = 0.0
        obs_ratio = min(days / BRIDGE_OBS_DAYS, 1.0) if BRIDGE_OBS_DAYS else 1.0
        score = (0.35 * (1.0 if format_known else 0.0)
                 + 0.15 * (1.0 if has_customers else 0.0)
                 + 0.10 * (1.0 if has_products else 0.0)
                 + 0.30 * dry_ratio
                 + 0.10 * obs_ratio)
        checklist = [
            {"key": "format", "label": "Formato del gestionale appreso", "done": format_known,
             "detail": "Profilo di export o adapter ERP attivo"},
            {"key": "customers", "label": "Anagrafica clienti sincronizzata", "done": has_customers,
             "detail": "Import codici cliente dall'ERP"},
            {"key": "products", "label": "Anagrafica prodotti sincronizzata", "done": has_products,
             "detail": "Import codici articolo/SKU dall'ERP"},
            {"key": "dry_runs", "label": f"Ordini di prova riusciti ({dry_runs}/{BRIDGE_DRY_RUN_TARGET})",
             "done": dry_runs >= BRIDGE_DRY_RUN_TARGET, "progress": round(dry_ratio, 2),
             "detail": "Consegne in modalità apprendimento andate a buon fine"},
            {"key": "observation", "label": f"Periodo di osservazione ({int(days)}/{BRIDGE_OBS_DAYS} giorni)",
             "done": obs_ratio >= 1.0, "progress": round(obs_ratio, 2),
             "detail": "Il Bridge osserva prima di scrivere per davvero"},
        ]
        return {"score": round(score, 3), "checklist": checklist,
                "dry_runs": dry_runs, "days_observed": round(days, 1),
                "threshold": BRIDGE_READY_THRESHOLD}

    async def recompute_readiness(agent_id: str):
        agent = await db.bridge_agents.find_one({"id": agent_id}, {"_id": 0})
        if not agent or not agent.get("paired"):
            return None
        r = await compute_readiness(agent)
        update = {"readiness": r["score"], "readiness_updated_at": now_iso()}
        promoted = agent.get("maturity") == "learning" and r["score"] >= BRIDGE_READY_THRESHOLD
        if promoted:
            update["maturity"] = "ready"
            update["ready_at"] = now_iso()
        await db.bridge_agents.update_one({"id": agent_id}, {"$set": update})
        if promoted:
            await create_notification(agent["company_id"], "bridge_ready",
                detail=f"{agent.get('erp_name') or agent.get('name')}: ha imparato abbastanza, pronto a inserire gli ordini automaticamente")
            await log_bridge_event(agent["company_id"], agent_id, "ready",
                "Ho imparato abbastanza: sono pronto a inserire gli ordini nel gestionale")
        return r

    async def recompute_company_agents(company_id: str):
        ids = await db.bridge_agents.distinct(
            "id", {"company_id": company_id, "maturity": {"$in": ["learning", "ready"]}})
        for aid in ids:
            await recompute_readiness(aid)

    # ---- Bridge resilience & observability ------------------------------------
    # Durable delivery queue (retry/backoff/TTL, reclaim), proactive offline
    # detection with delivery-on-wake, adapter circuit-breaker, and a "Bridge diary"
    # so the learning week feels like visible progress, not silence.
    BRIDGE_OFFLINE_MIN = int(os.environ.get("BRIDGE_OFFLINE_MIN", "5"))
    BRIDGE_JOB_MAX_ATTEMPTS = 5
    BRIDGE_JOB_TTL_DAYS = 7
    BRIDGE_CLAIM_TIMEOUT_MIN = 5
    ADAPTER_CB_MIN_DELIVERIES = 5   # data needed before the breaker can trip
    ADAPTER_CB_MIN_RATE = 0.85      # windowed success-rate floor
    ADAPTER_CB_WINDOW = 20          # rolling window of recent outcomes

    async def log_bridge_event(company_id: str, agent_id: Optional[str], kind: str, message: str):
        await db.bridge_events.insert_one({
            "id": str(uuid.uuid4()), "company_id": company_id, "agent_id": agent_id,
            "kind": kind, "message": message, "created_at": now_iso()})

    def _backoff_seconds(attempts: int) -> int:
        return min(60 * (2 ** max(attempts - 1, 0)), 3600)

    async def mark_agent_online(agent: dict):
        """Set online; if it was offline, announce recovery + pending backlog (delivery-on-wake)."""
        if agent.get("status") == "offline":
            pending = await db.delivery_jobs.count_documents(
                {"agent_id": agent["id"], "status": {"$in": ["pending", "claimed"]}})
            await create_notification(agent["company_id"], "bridge_recovered",
                detail=(f"{pending} ordini in consegna al risveglio" if pending else "Bridge di nuovo online"))
            await log_bridge_event(agent["company_id"], agent["id"], "recovered",
                (f"Tornato online — {pending} ordini in coda da consegnare" if pending else "Tornato online"))
        await db.bridge_agents.update_one({"id": agent["id"]},
            {"$set": {"last_seen": now_iso(), "status": "online"}})

    async def bridge_monitor_loop():
        """Proactively flag agents that went silent so the operator hears it from Ordia first."""
        while True:
            try:
                cutoff = (datetime.now(timezone.utc) - timedelta(minutes=BRIDGE_OFFLINE_MIN)).isoformat()
                agents = await db.bridge_agents.find(
                    {"paired": True, "status": {"$ne": "offline"},
                     "maturity": {"$in": ["learning", "ready", "active"]},
                     "last_seen": {"$lt": cutoff}}, {"_id": 0}).to_list(200)
                for ag in agents:
                    await db.bridge_agents.update_one({"id": ag["id"]}, {"$set": {"status": "offline"}})
                    await create_notification(ag["company_id"], "bridge_offline",
                        detail=f"{ag.get('erp_name') or ag.get('name')}: nessun contatto da {BRIDGE_OFFLINE_MIN} min")
                    await log_bridge_event(ag["company_id"], ag["id"], "offline",
                        "Bridge offline — nessun contatto")
            except Exception as e:
                logger.warning("bridge_monitor error: %s", e)
            await asyncio.sleep(60)

    class AgentCreate(BaseModel):
        name: str = "Ordia Bridge"
        erp_name: str = ""
        profile_id: Optional[str] = None

    class AgentUpdate(BaseModel):
        name: Optional[str] = None
        erp_name: Optional[str] = None
        profile_id: Optional[str] = None
        active: Optional[bool] = None

    @api.post("/bridge/agents")
    async def create_bridge_agent(body: AgentCreate, user: dict = Depends(get_current_user)):
        require_privileged(user)
        code = _gen_pairing_code()
        while await db.bridge_agents.find_one({"pairing_code": code, "paired": False}):
            code = _gen_pairing_code()
        doc = {
            "id": str(uuid.uuid4()), "company_id": user["company_id"], "name": body.name,
            "erp_name": body.erp_name, "profile_id": body.profile_id,
            "pairing_code": code, "token": None, "paired": False, "active": True,
            "status": "unpaired", "maturity": "unpaired", "last_seen": None, "created_at": now_iso(),
        }
        await db.bridge_agents.insert_one(dict(doc))
        doc.pop("_id", None)
        return doc  # pairing_code returned in clear (needed once by the agent)

    @api.get("/bridge/agents")
    async def list_bridge_agents(user: dict = Depends(get_current_user)):
        agents = await db.bridge_agents.find({"company_id": user["company_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)
        return [_agent_public(a) for a in agents]

    @api.put("/bridge/agents/{agent_id}")
    async def update_bridge_agent(agent_id: str, body: AgentUpdate, user: dict = Depends(get_current_user)):
        require_privileged(user)
        update = {k: v for k, v in body.model_dump().items() if v is not None}
        res = await db.bridge_agents.update_one({"id": agent_id, "company_id": user["company_id"]}, {"$set": update})
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Agente non trovato")
        if "profile_id" in update:
            await recompute_readiness(agent_id)
        return _agent_public(await db.bridge_agents.find_one({"id": agent_id}, {"_id": 0}))

    @api.get("/bridge/agents/{agent_id}/readiness")
    async def get_agent_readiness(agent_id: str, user: dict = Depends(get_current_user)):
        agent = await db.bridge_agents.find_one({"id": agent_id, "company_id": user["company_id"]}, {"_id": 0})
        if not agent:
            raise HTTPException(status_code=404, detail="Agente non trovato")
        r = await compute_readiness(agent)
        if agent.get("paired"):
            await recompute_readiness(agent_id)
            agent = await db.bridge_agents.find_one({"id": agent_id}, {"_id": 0})
        return {"agent": _agent_public(agent), **r}

    @api.post("/bridge/agents/{agent_id}/activate")
    async def activate_bridge_agent(agent_id: str, user: dict = Depends(get_current_user)):
        """Operator turns learning/ready Bridge into live auto-insertion. Guarded by readiness."""
        require_privileged(user)
        agent = await db.bridge_agents.find_one({"id": agent_id, "company_id": user["company_id"]}, {"_id": 0})
        if not agent:
            raise HTTPException(status_code=404, detail="Agente non trovato")
        if agent.get("maturity") != "ready":
            r = await compute_readiness(agent)
            if r["score"] < BRIDGE_READY_THRESHOLD:
                raise HTTPException(status_code=400,
                    detail="Il Bridge non ha ancora imparato abbastanza per l'inserimento automatico")
        await db.bridge_agents.update_one({"id": agent_id},
            {"$set": {"maturity": "active", "activated_at": now_iso()}})
        return _agent_public(await db.bridge_agents.find_one({"id": agent_id}, {"_id": 0}))

    @api.post("/bridge/agents/{agent_id}/pause")
    async def pause_bridge_agent(agent_id: str, user: dict = Depends(get_current_user)):
        """Send an active Bridge back to learning (shadow) mode — orders stop being written for real."""
        require_privileged(user)
        res = await db.bridge_agents.update_one(
            {"id": agent_id, "company_id": user["company_id"], "paired": True},
            {"$set": {"maturity": "learning"}})
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Agente non trovato")
        return _agent_public(await db.bridge_agents.find_one({"id": agent_id}, {"_id": 0}))

    @api.delete("/bridge/agents/{agent_id}")
    async def delete_bridge_agent(agent_id: str, user: dict = Depends(get_current_user)):
        require_privileged(user)
        await db.bridge_agents.delete_one({"id": agent_id, "company_id": user["company_id"]})
        return {"ok": True}

    class PairBody(BaseModel):
        pairing_code: str

    @api.post("/bridge/pair")
    async def bridge_pair(body: PairBody):
        """Called by the local agent with the 6-digit code shown in the dashboard.
        One-time: consumes the code and returns a long-lived agent token."""
        agent = await db.bridge_agents.find_one({"pairing_code": body.pairing_code, "paired": False})
        if not agent:
            raise HTTPException(status_code=404, detail="Codice non valido o già usato")
        token = secrets.token_urlsafe(32)
        await db.bridge_agents.update_one({"id": agent["id"]}, {"$set": {
            "token": token, "paired": True, "status": "online", "pairing_code": None,
            "paired_at": now_iso(), "last_seen": now_iso(),
            "maturity": "learning", "learning_started_at": now_iso(),
            "dry_runs": 0, "readiness": 0.0}})
        await create_notification(agent["company_id"], "bridge_learning",
            detail=f"{agent.get('erp_name') or agent.get('name')}: accoppiato, ora impara il tuo gestionale")
        await log_bridge_event(agent["company_id"], agent["id"], "paired",
            "Accoppiato — inizio l'apprendimento del tuo gestionale")
        return {"agent_id": agent["id"], "company_id": agent["company_id"],
                "name": agent["name"], "token": token}

    async def get_current_agent(request: Request) -> dict:
        token = request.headers.get("X-Bridge-Token", "")
        if not token:
            raise HTTPException(status_code=401, detail="Bridge token mancante")
        agent = await db.bridge_agents.find_one({"token": token, "paired": True}, {"_id": 0})
        if not agent:
            raise HTTPException(status_code=401, detail="Bridge token non valido")
        return agent

    async def enqueue_bridge_delivery(company_id: str, order: dict):
        """Approved order -> Bridge delivery queue. Renders with the agent's profile if set.
        The order is already persisted, so a failed delivery never loses it."""
        agent = await db.bridge_agents.find_one(
            {"company_id": company_id, "paired": True, "active": True}, {"_id": 0})
        if not agent:
            return None
        company = await db.companies.find_one({"id": company_id}, {"_id": 0}) or {}
        std = standardize_order(order, company)
        rendered, rendered_format = None, None
        if agent.get("profile_id"):
            profile = await db.export_profiles.find_one(
                {"id": agent["profile_id"], "company_id": company_id}, {"_id": 0})
            if profile:
                try:
                    content, _mt, ext = render_with_profile(std, profile)
                    rendered = content if isinstance(content, str) else base64.b64encode(content).decode("utf-8")
                    rendered_format = ext
                except Exception as e:
                    logger.warning("Bridge render failed: %s", e)
        job = {
            "id": str(uuid.uuid4()), "company_id": company_id, "agent_id": agent["id"],
            "order_id": order["id"], "customer_name": order.get("customer_name"),
            "profile_id": agent.get("profile_id"), "erp_name": agent.get("erp_name"),
            "standard_order": std, "rendered": rendered, "rendered_format": rendered_format,
            "mode": "live" if agent.get("maturity") == "active" else "shadow",
            "status": "pending", "attempts": 0, "max_attempts": BRIDGE_JOB_MAX_ATTEMPTS,
            "next_attempt_at": now_iso(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=BRIDGE_JOB_TTL_DAYS)).isoformat(),
            "result": None, "error": None,
            "created_at": now_iso(), "updated_at": now_iso(),
        }
        await db.delivery_jobs.insert_one(dict(job))
        job.pop("_id", None)
        logger.info("Bridge delivery queued job=%s order=%s agent=%s", job["id"], order["id"], agent["id"])
        return job

    @api.get("/bridge/relay/poll")
    async def bridge_relay_poll(agent: dict = Depends(get_current_agent)):
        await mark_agent_online(agent)
        now = now_iso()
        # Reclaim jobs stuck in 'claimed' (agent died mid-delivery) so they retry.
        stale = (datetime.now(timezone.utc) - timedelta(minutes=BRIDGE_CLAIM_TIMEOUT_MIN)).isoformat()
        await db.delivery_jobs.update_many(
            {"agent_id": agent["id"], "status": "claimed", "claimed_at": {"$lt": stale}},
            {"$set": {"status": "pending"}})
        jobs = await db.delivery_jobs.find(
            {"agent_id": agent["id"], "status": "pending",
             "$or": [{"next_attempt_at": {"$lte": now}}, {"next_attempt_at": None},
                     {"next_attempt_at": {"$exists": False}}]},
            {"_id": 0}).sort("created_at", 1).to_list(20)
        for j in jobs:
            await db.delivery_jobs.update_one({"id": j["id"]}, {"$set": {"status": "claimed", "claimed_at": now}})
        return {"jobs": jobs, "count": len(jobs)}

    class AckBody(BaseModel):
        job_id: str
        status: str  # delivered | exception
        result: Optional[dict] = None
        error: Optional[str] = None

    @api.post("/bridge/relay/ack")
    async def bridge_relay_ack(body: AckBody, agent: dict = Depends(get_current_agent)):
        job = await db.delivery_jobs.find_one({"id": body.job_id, "agent_id": agent["id"]}, {"_id": 0})
        if not job:
            raise HTTPException(status_code=404, detail="Job non trovato")
        if job.get("status") in ("delivered", "failed"):
            return {"ok": True, "already": job["status"]}  # idempotent: no double side-effects
        delivered = body.status == "delivered"
        if delivered:
            await db.delivery_jobs.update_one({"id": job["id"]}, {
                "$set": {"status": "delivered", "result": body.result, "error": None, "updated_at": now_iso()},
                "$inc": {"attempts": 1}})
            if job.get("mode") == "shadow":
                # Learning mode: this was a test/draft insertion, not the final order.
                # Count it toward readiness; never mark the order as exported.
                await db.bridge_agents.update_one({"id": agent["id"]}, {"$inc": {"dry_runs": 1}})
                await db.orders.update_one({"id": job["order_id"], "company_id": agent["company_id"]}, {
                    "$push": {"history": history_entry("Consegna di prova nel gestionale (apprendimento Bridge)",
                                                       "bridge", agent.get("erp_name") or agent["name"])}})
                await log_bridge_event(agent["company_id"], agent["id"], "dry_run",
                    f"Preparata una bozza di prova corretta per {job.get('customer_name') or 'un cliente'}")
                await recompute_readiness(agent["id"])
            else:
                await db.orders.update_one({"id": job["order_id"], "company_id": agent["company_id"]}, {
                    "$set": {"status": "exported", "updated_at": now_iso()},
                    "$push": {"history": history_entry("Consegnato nel gestionale (Bridge)", "bridge",
                                                       agent.get("erp_name") or agent["name"])}})
                await create_notification(agent["company_id"], "bridge_delivered",
                                          customer_name=job.get("customer_name"), order_id=job["order_id"],
                                          detail=f"Consegnato in {agent.get('erp_name') or 'gestionale'}")
            return {"ok": True}
        # Exception: retry with exponential backoff until max attempts / TTL, then fail.
        attempts = (job.get("attempts", 0) or 0) + 1
        max_att = job.get("max_attempts", BRIDGE_JOB_MAX_ATTEMPTS)
        expired = bool(job.get("expires_at")) and job["expires_at"] < now_iso()
        if attempts < max_att and not expired:
            backoff = _backoff_seconds(attempts)
            next_at = (datetime.now(timezone.utc) + timedelta(seconds=backoff)).isoformat()
            await db.delivery_jobs.update_one({"id": job["id"]}, {
                "$set": {"status": "pending", "error": body.error, "next_attempt_at": next_at, "updated_at": now_iso()},
                "$inc": {"attempts": 1}})
            return {"ok": True, "retry_in": backoff, "attempt": attempts}
        await db.delivery_jobs.update_one({"id": job["id"]}, {
            "$set": {"status": "failed", "error": body.error, "updated_at": now_iso()},
            "$inc": {"attempts": 1}})
        await create_notification(agent["company_id"], "bridge_exception",
                                  customer_name=job.get("customer_name"), order_id=job["order_id"],
                                  detail=(body.error or "Consegna non riuscita")[:160])
        return {"ok": True, "failed": True}

    @api.post("/bridge/relay/heartbeat")
    async def bridge_relay_heartbeat(agent: dict = Depends(get_current_agent)):
        await mark_agent_online(agent)
        return {"ok": True, "server_time": now_iso()}

    @api.get("/bridge/jobs")
    async def list_delivery_jobs(status: Optional[str] = None, user: dict = Depends(get_current_user)):
        q = {"company_id": user["company_id"]}
        if status:
            q["status"] = status
        return await db.delivery_jobs.find(
            q, {"_id": 0, "standard_order": 0, "rendered": 0}).sort("created_at", -1).to_list(200)

    # ---- ERP Adapter Profiles (learned UI recipes) + network effect -------------
    # An adapter is the LEARNED recipe to drive a given ERP's UI. It is company-agnostic
    # (a UI recipe), so once one customer learns & confirms an ERP, every other customer
    # on the same ERP inherits it (network effect). Master-data (codes) stays per-company.
    class AdapterBody(BaseModel):
        erp_key: str                 # e.g. "odoo/18"
        erp_guess: str = ""
        spec: dict                   # customer_field, product_field, qty_field, selectors...
        confidence: float = 0.0
        test_order_ref: Optional[str] = None

    @api.post("/bridge/adapters")
    async def submit_adapter(body: AdapterBody, agent: dict = Depends(get_current_agent)):
        """Called by the agent after LEARNING an ERP. Saved as pending_confirmation until
        a human confirms the test order it produced."""
        prev = await db.erp_adapters.find({"erp_key": body.erp_key}).sort("version", -1).to_list(1)
        version = (prev[0]["version"] + 1) if prev else 1
        doc = {
            "id": str(uuid.uuid4()), "erp_key": body.erp_key, "erp_guess": body.erp_guess,
            "spec": body.spec, "confidence": body.confidence, "source_company_id": agent["company_id"],
            "test_order_ref": body.test_order_ref, "verified": False, "status": "pending_confirmation",
            "version": version, "deliveries": 0, "successes": 0, "failures": 0, "heal_count": 0,
            "last_used": None, "created_at": now_iso(), "updated_at": now_iso(),
        }
        await db.erp_adapters.insert_one(dict(doc))
        doc.pop("_id", None)
        await create_notification(agent["company_id"], "adapter_pending",
                                  detail=f"{body.erp_guess or body.erp_key}: conferma l'ordine di prova {body.test_order_ref or ''}".strip())
        return _with_rate(doc)

    def _with_rate(a: dict) -> dict:
        d = a.get("deliveries", 0) or 0
        a["success_rate"] = round((a.get("successes", 0) / d), 3) if d else None
        return a

    @api.get("/bridge/adapters")
    async def list_adapters(user: dict = Depends(get_current_user)):
        """Own pending adapters + all verified/active adapters (network effect)."""
        docs = await db.erp_adapters.find(
            {"$or": [{"source_company_id": user["company_id"]}, {"status": "active"}]},
            {"_id": 0}).sort([("erp_key", 1), ("version", -1)]).to_list(200)
        return [_with_rate(d) for d in docs]

    @api.get("/bridge/adapters/resolve")
    async def resolve_adapter(erp_key: str, agent: dict = Depends(get_current_agent)):
        """Agent fetches the BEST active adapter for an ERP — inherited across customers.
        Ranking: proven success rate first, then most recent version (new versions still
        get a fair trial before enough data exists)."""
        docs = await db.erp_adapters.find(
            {"erp_key": erp_key, "status": "active"}, {"_id": 0}).to_list(50)
        if not docs:
            raise HTTPException(status_code=404, detail="Nessun adapter attivo per questo ERP")
        def rank(a):
            d = a.get("deliveries", 0) or 0
            rate = (a.get("successes", 0) / d) if d else 0.75  # unproven adapters get a fair trial
            return (round(rate, 3), a.get("version", 0))
        best = sorted(docs, key=rank, reverse=True)[0]
        return _with_rate(best)

    class AdapterReport(BaseModel):
        status: str  # success | failure

    @api.post("/bridge/adapters/{adapter_id}/report")
    async def report_adapter_outcome(adapter_id: str, body: AdapterReport, agent: dict = Depends(get_current_agent)):
        """Agent reports a delivery outcome. Metrics drive future selection AND a circuit
        breaker: an active adapter whose recent success-rate drops below the floor is
        auto-quarantined so it stops contaminating the shared network."""
        ok = body.status == "success"
        inc = {"deliveries": 1, "successes" if ok else "failures": 1}
        await db.erp_adapters.update_one({"id": adapter_id}, {
            "$inc": inc, "$set": {"last_used": now_iso()},
            "$push": {"recent": {"$each": ["s" if ok else "f"], "$slice": -ADAPTER_CB_WINDOW}}})
        a = await db.erp_adapters.find_one({"id": adapter_id}, {"_id": 0})
        if not a:
            raise HTTPException(status_code=404, detail="Adapter non trovato")
        recent = a.get("recent", []) or []
        if a.get("status") == "active" and len(recent) >= ADAPTER_CB_MIN_DELIVERIES:
            rate = recent.count("s") / len(recent)
            if rate < ADAPTER_CB_MIN_RATE:
                await db.erp_adapters.update_one({"id": adapter_id},
                    {"$set": {"status": "quarantined", "quarantined_at": now_iso()}})
                await create_notification(agent["company_id"], "adapter_quarantined",
                    detail=f"{a.get('erp_guess') or a.get('erp_key')}: affidabilità {int(rate*100)}% — messo in quarantena, riapprendo")
                await log_bridge_event(agent["company_id"], agent["id"], "quarantine",
                    f"Adapter {a.get('erp_key')} in quarantena (affidabilità {int(rate*100)}%)")
        return {"ok": True}

    @api.post("/bridge/adapters/{adapter_id}/confirm")
    async def confirm_adapter(adapter_id: str, user: dict = Depends(get_current_user)):
        """Human confirms the test order is correct -> adapter goes ACTIVE (shared)."""
        require_privileged(user)
        adapter = await db.erp_adapters.find_one({"id": adapter_id}, {"_id": 0})
        if not adapter:
            raise HTTPException(status_code=404, detail="Adapter non trovato")
        await db.erp_adapters.update_one(
            {"id": adapter_id}, {"$set": {"verified": True, "status": "active",
                                          "verified_by": user["company_id"], "updated_at": now_iso()}})
        await recompute_company_agents(user["company_id"])
        await log_bridge_event(user["company_id"], None, "adapter_active",
            f"ERP {adapter.get('erp_guess') or adapter.get('erp_key')} attivato — pronto per le consegne")
        return await db.erp_adapters.find_one({"id": adapter_id}, {"_id": 0})

    @api.put("/bridge/adapters/{adapter_id}/heal")
    async def heal_adapter(adapter_id: str, body: AdapterBody, agent: dict = Depends(get_current_agent)):
        """Self-healing: the agent re-learned the UI (it changed) and pushes an updated spec.
        A quarantined adapter is brought back to active with a fresh outcome window."""
        adapter = await db.erp_adapters.find_one({"id": adapter_id}, {"_id": 0})
        if not adapter:
            raise HTTPException(status_code=404, detail="Adapter non trovato")
        upd = {"spec": body.spec, "confidence": body.confidence,
               "updated_at": now_iso(), "healed_at": now_iso(), "recent": []}
        if adapter.get("status") == "quarantined":
            upd["status"] = "active"
        await db.erp_adapters.update_one({"id": adapter_id}, {"$set": upd, "$inc": {"heal_count": 1}})
        await log_bridge_event(agent["company_id"], agent["id"], "healed",
            f"Interfaccia di {adapter.get('erp_key')} cambiata: mi sono auto-riparato")
        return await db.erp_adapters.find_one({"id": adapter_id}, {"_id": 0})

    # ---- Master-data sync (ERP code lists) -> makes mapping "safe" ---------------
    class MasterDataBody(BaseModel):
        erp_key: str
        kind: str                    # customer | product | tax
        entries: List[dict]          # [{erp_id, code, name}]

    @api.post("/bridge/master-data")
    async def upsert_master_data(body: MasterDataBody, agent: dict = Depends(get_current_agent)):
        """Agent imports the ERP's code lists so canonical->ERP mapping resolves to real codes."""
        doc = {"company_id": agent["company_id"], "erp_key": body.erp_key, "kind": body.kind,
               "entries": body.entries, "count": len(body.entries), "updated_at": now_iso()}
        await db.erp_master_data.update_one(
            {"company_id": agent["company_id"], "erp_key": body.erp_key, "kind": body.kind},
            {"$set": doc}, upsert=True)
        await recompute_company_agents(agent["company_id"])
        kind_it = {"customer": "clienti", "product": "prodotti/SKU", "tax": "aliquote IVA"}.get(body.kind, body.kind)
        await log_bridge_event(agent["company_id"], agent["id"], "master_data",
            f"Imparati {len(body.entries)} {kind_it} dal gestionale")
        return {"ok": True, "kind": body.kind, "count": len(body.entries)}

    @api.get("/bridge/agents/{agent_id}/diary")
    async def bridge_diary(agent_id: str, user: dict = Depends(get_current_user)):
        """The Bridge diary: a human-readable feed of what the agent learned/did, so the
        learning period feels like visible progress instead of silence."""
        agent = await db.bridge_agents.find_one({"id": agent_id, "company_id": user["company_id"]}, {"_id": 0})
        if not agent:
            raise HTTPException(status_code=404, detail="Agente non trovato")
        return await db.bridge_events.find(
            {"company_id": user["company_id"], "$or": [{"agent_id": agent_id}, {"agent_id": None}]},
            {"_id": 0}).sort("created_at", -1).to_list(30)

    # ---- Weekly Bridge summary (turns the learning wait into visible progress) ---
    async def build_weekly_summary(company_id: str) -> dict:
        since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        events = await db.bridge_events.find(
            {"company_id": company_id, "created_at": {"$gte": since}},
            {"_id": 0}).sort("created_at", -1).to_list(1000)
        by_kind = {}
        for e in events:
            by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
        md = await db.erp_master_data.find({"company_id": company_id}, {"_id": 0, "entries": 0}).to_list(50)
        agents = await db.bridge_agents.find(
            {"company_id": company_id, "paired": True}, {"_id": 0}).to_list(50)
        return {
            "period_days": 7,
            "drafts_prepared": by_kind.get("dry_run", 0),
            "codes_in_catalog": sum(m.get("count", 0) for m in md),
            "self_heals": by_kind.get("healed", 0),
            "erps_activated": by_kind.get("adapter_active", 0),
            "agents_ready": sum(1 for a in agents if a.get("maturity") == "ready"),
            "agents_active": sum(1 for a in agents if a.get("maturity") == "active"),
            "agents": [{"name": a.get("erp_name") or a.get("name"), "maturity": a.get("maturity"),
                        "readiness": a.get("readiness", 0), "dry_runs": a.get("dry_runs", 0)} for a in agents],
            "events_count": len(events),
            "highlights": [e["message"] for e in events[:5]],
        }

    def render_summary_email(company_name: str, s: dict):
        subject = "Ordia · Il tuo Bridge questa settimana"
        hi = "".join(f"<li style='margin:4px 0;color:#334155'>{m}</li>" for m in s.get("highlights", [])) \
             or "<li style='color:#94A3B8'>Nessuna attività registrata.</li>"
        ready_line = ""
        if s["agents_ready"]:
            ready_line = (f"<p style='margin:16px 0;padding:12px 14px;background:#EFF6FF;border-radius:8px;"
                          f"color:#1D4ED8;font-weight:600'>⚡ {s['agents_ready']} Bridge è pronto a inserire "
                          f"gli ordini automaticamente — attivalo con un click in Ordia.</p>")
        html = f"""<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;margin:0 auto">
      <h2 style="color:#0B1E3B;margin:0 0 4px">Il tuo Ordia Bridge questa settimana</h2>
      <p style="color:#64748B;margin:0 0 20px">{company_name} · ultimi 7 giorni</p>
      <table style="width:100%;border-collapse:collapse;margin-bottom:8px">
        <tr>
          <td style="padding:14px;background:#F8FAFC;border-radius:8px;text-align:center">
            <div style="font-size:26px;font-weight:800;color:#0B1E3B">{s['drafts_prepared']}</div>
            <div style="font-size:12px;color:#64748B">bozze di prova corrette</div></td>
          <td style="width:12px"></td>
          <td style="padding:14px;background:#F8FAFC;border-radius:8px;text-align:center">
            <div style="font-size:26px;font-weight:800;color:#0B1E3B">{s['codes_in_catalog']}</div>
            <div style="font-size:12px;color:#64748B">codici in anagrafica</div></td>
          <td style="width:12px"></td>
          <td style="padding:14px;background:#F8FAFC;border-radius:8px;text-align:center">
            <div style="font-size:26px;font-weight:800;color:#0B1E3B">{s['self_heals']}</div>
            <div style="font-size:12px;color:#64748B">auto-riparazioni</div></td>
        </tr>
      </table>
      {ready_line}
      <h3 style="color:#0B1E3B;margin:20px 0 6px;font-size:15px">Cosa ho imparato</h3>
      <ul style="margin:0;padding-left:18px;font-size:14px">{hi}</ul>
      <p style="margin:24px 0 0;color:#94A3B8;font-size:12px">Ordia impara il tuo gestionale per eliminare la digitazione degli ordini.</p>
    </div>"""
        return subject, html

    @api.get("/bridge/weekly-summary")
    async def weekly_summary_preview(user: dict = Depends(get_current_user)):
        return await build_weekly_summary(user["company_id"])

    class SummarySendBody(BaseModel):
        recipient_email: Optional[str] = None

    @api.post("/bridge/weekly-summary/send")
    async def weekly_summary_send(body: SummarySendBody, user: dict = Depends(get_current_user)):
        require_privileged(user)
        if not RESEND_API_KEY:
            raise HTTPException(status_code=400, detail="Integrazione email non configurata. Aggiungi RESEND_API_KEY.")
        company = await db.companies.find_one({"id": user["company_id"]}, {"_id": 0}) or {}
        s = await build_weekly_summary(user["company_id"])
        subject, html = render_summary_email(company.get("name") or "la tua azienda", s)
        to = body.recipient_email or user["email"]
        try:
            await asyncio.to_thread(resend.Emails.send,
                                    {"from": SENDER_EMAIL, "to": [to], "subject": subject, "html": html})
        except Exception as e:
            logger.error("weekly summary send failed: %s", e)
            raise HTTPException(status_code=502, detail=f"Invio non riuscito: {e}")
        await db.companies.update_one({"id": user["company_id"]}, {"$set": {"last_summary_at": now_iso()}})
        return {"ok": True, "sent_to": to, "summary": s}

    async def weekly_summary_loop():
        """Autonomous weekly digest to company admins. Off by default (test-mode Resend
        only delivers to the account inbox); enable with BRIDGE_WEEKLY_SUMMARY=1."""
        if os.environ.get("BRIDGE_WEEKLY_SUMMARY", "0") != "1" or not RESEND_API_KEY:
            return
        while True:
            try:
                week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
                company_ids = await db.bridge_agents.distinct("company_id", {"paired": True})
                for cid in company_ids:
                    company = await db.companies.find_one({"id": cid}, {"_id": 0}) or {}
                    if company.get("last_summary_at") and company["last_summary_at"] > week_ago:
                        continue
                    admin = await db.users.find_one({"company_id": cid, "role": "admin"}, {"_id": 0})
                    if not admin:
                        continue
                    s = await build_weekly_summary(cid)
                    subject, html = render_summary_email(company.get("name") or "la tua azienda", s)
                    try:
                        await asyncio.to_thread(resend.Emails.send,
                            {"from": SENDER_EMAIL, "to": [admin["email"]], "subject": subject, "html": html})
                        await db.companies.update_one({"id": cid}, {"$set": {"last_summary_at": now_iso()}})
                    except Exception as e:
                        logger.warning("weekly summary loop send failed for %s: %s", cid, e)
            except Exception as e:
                logger.warning("weekly_summary_loop error: %s", e)
            await asyncio.sleep(6 * 3600)


    @api.get("/bridge/master-data")
    async def get_master_data(user: dict = Depends(get_current_user)):
        docs = await db.erp_master_data.find(
            {"company_id": user["company_id"]}, {"_id": 0, "entries": 0}).to_list(50)
        return docs



    return {
        "enqueue_bridge_delivery": enqueue_bridge_delivery,
        "bridge_monitor_loop": bridge_monitor_loop,
        "weekly_summary_loop": weekly_summary_loop,
    }
