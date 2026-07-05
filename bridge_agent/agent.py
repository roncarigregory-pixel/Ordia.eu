#!/usr/bin/env python3
"""Ordia Bridge — reference agent (for end-to-end flow validation over HTTP).

This is NOT the production distributable (no signing/auto-update). It proves the
cloud backbone: pair with a 6-digit code, poll the relay, "deliver" approved
orders into the ERP (here: simulated / write file), and acknowledge.

Usage:
  python agent.py --backend https://<host> --pair 123456          # first run: pair
  python agent.py --backend https://<host> --token <TOKEN>        # run loop
  python agent.py --backend https://<host> --pair 123456 --once   # pair + one poll cycle
"""
import argparse
import os
import time
import json
import sys
import urllib.request
import urllib.error

STATE_FILE = os.environ.get("ORDIA_BRIDGE_STATE", os.path.join(os.path.dirname(__file__), ".agent_state.json"))
OUT_DIR = os.environ.get("ORDIA_BRIDGE_OUTDIR", os.path.join(os.path.dirname(__file__), "delivered"))
CONFIG_FILE = os.environ.get("ORDIA_BRIDGE_CONFIG", os.path.join(os.path.dirname(__file__), "config.json"))


def load_config():
    """Local delivery config (stays on-prem with the agent — never in the cloud).
    { "delivery_mode": "file" | "rpa_odoo", "odoo_url", "login", "password",
      "customer_map", "product_map", "default_customer", "default_product" }"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
    else:
        cfg = {"delivery_mode": "file"}
    if os.environ.get("ORDIA_DELIVERY_MODE"):
        cfg["delivery_mode"] = os.environ["ORDIA_DELIVERY_MODE"]
    return cfg


def _req(method, url, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json", "User-Agent": "OrdiaBridge/1.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def pair(backend, code):
    status, data = _req("POST", f"{backend}/api/bridge/pair", {"pairing_code": code})
    if status != 200:
        print(f"[pair] FAILED {status}: {data}")
        sys.exit(1)
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)
    print(f"[pair] OK — paired as '{data.get('name')}' (agent {data.get('agent_id')})")
    return data["token"]


def load_token():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f).get("token")
    return None


def deliver(job, config, backend=None, token=None):
    """Deliver the approved order into the ERP using the configured channel.
      - rpa_learned: resolve the ACTIVE learned adapter from Ordia, deliver via the
        self-healing generic replay engine, and report the outcome (metrics/network effect).
      - rpa_odoo: drive the ERP web UI with a local static profile.
      - odoo_api: create the order via the ERP API.
      - file (default): write the rendered/canonical payload to disk."""
    mode = config.get("delivery_mode", "file")
    if mode == "desktop_uia":
        import asyncio
        from replay_desktop import deliver_via_desktop
        std = job.get("standard_order") or {}
        res = asyncio.run(deliver_via_desktop(std, config, backend, token))
        print(f"[deliver:desktop_uia] order {job['order_id'][:8]} -> {res.get('lines')} righe "
              f"(adapter v{res.get('adapter_version')})")
        return {"channel": "desktop_uia", "erp": job.get("erp_name"), **res}
    if mode == "rpa_learned":
        import asyncio
        from rpa_replay import replay_with_healing
        erp_key = config.get("erp_key", "odoo/18")
        st, adapter = _req("GET", f"{backend}/api/bridge/adapters/resolve?erp_key={erp_key}",
                           headers={"X-Bridge-Token": token})
        if st != 200:
            raise RuntimeError(f"Nessun adapter attivo per {erp_key} (HTTP {st}) — apprendi e conferma l'ERP prima")
        adapter_id = adapter["id"]
        print(f"[deliver:rpa_learned] adapter v{adapter.get('version')} conf {adapter.get('confidence')} "
              f"success_rate={adapter.get('success_rate')} heals={adapter.get('heal_count')}")
        std = job.get("standard_order") or {}
        try:
            res = asyncio.run(replay_with_healing(adapter["spec"], std, config, backend, token, adapter_id))
            _req("POST", f"{backend}/api/bridge/adapters/{adapter_id}/report",
                 {"status": "success"}, {"X-Bridge-Token": token})
            print(f"[deliver:rpa_learned] order {job['order_id'][:8]} -> {res.get('order_ref')}")
            return {"channel": "rpa_learned", "erp": job.get("erp_name"), "adapter_version": adapter.get("version"), **res}
        except Exception:
            _req("POST", f"{backend}/api/bridge/adapters/{adapter_id}/report",
                 {"status": "failure"}, {"X-Bridge-Token": token})
            raise
    if mode == "rpa_odoo":
        import asyncio
        from rpa_odoo import deliver_via_rpa
        std = job.get("standard_order") or {}
        res = asyncio.run(deliver_via_rpa(std, config))
        print(f"[deliver:rpa] order {job['order_id'][:8]} -> Odoo {res.get('order_ref')} "
              f"(customer '{res.get('customer')}', {res.get('lines')} lines)")
        return {"channel": "rpa_odoo", "erp": job.get("erp_name"), **res}
    if mode == "odoo_api":
        import asyncio
        from odoo_api import deliver_via_api
        std = job.get("standard_order") or {}
        res = asyncio.run(deliver_via_api(std, config))
        print(f"[deliver:api] order {job['order_id'][:8]} -> Odoo {res.get('order_ref')} "
              f"(customer '{res.get('customer')}', {res.get('lines')} lines, total {res.get('total')})")
        return {"channel": "odoo_api", "erp": job.get("erp_name"), **res}

    os.makedirs(OUT_DIR, exist_ok=True)
    ext = job.get("rendered_format") or "json"
    payload = job.get("rendered") or json.dumps(job.get("standard_order", {}), ensure_ascii=False, indent=2)
    path = os.path.join(OUT_DIR, f"order-{job['order_id'][:8]}.{ext}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(payload)
    print(f"[deliver:file] order {job['order_id'][:8]} -> {path}")
    return {"channel": "file", "delivered_to": path, "erp": job.get("erp_name")}


def _maybe_sync_catalog(backend, token, config, state):
    """Periodic ERP->Ordia catalog/master-data sync (on-prem, has ERP access).
    Enabled by config 'catalog_sync_hours' > 0. State tracks last run to throttle."""
    hours = float(config.get("catalog_sync_hours", 0) or 0)
    if hours <= 0:
        return
    last = state.get("last_catalog_sync_ts", 0)
    if (time.time() - last) < hours * 3600:
        return
    try:
        from master_data_import import run_sync
        run_sync(backend, token)
        state["last_catalog_sync_ts"] = time.time()
        print(f"[catalog-sync] completato (prossimo tra ~{hours}h)")
    except Exception as e:
        print(f"[catalog-sync] errore: {e}")


def cycle(backend, token, config):
    headers = {"X-Bridge-Token": token}
    status, data = _req("GET", f"{backend}/api/bridge/relay/poll", headers=headers)
    if status != 200:
        print(f"[poll] {status}: {data}")
        return
    jobs = data.get("jobs", [])
    if jobs:
        print(f"[poll] {len(jobs)} job(s) claimed")
    for job in jobs:
        mode = job.get("mode", "live")
        try:
            result = deliver(job, config, backend, token)
            result = {**result, "mode": mode}
            _req("POST", f"{backend}/api/bridge/relay/ack",
                 {"job_id": job["id"], "status": "delivered", "result": result}, headers=headers)
            print(f"[ack] delivered {job['id']} (mode={mode}"
                  f"{' — apprendimento/bozza' if mode == 'shadow' else ''})")
        except Exception as e:
            _req("POST", f"{backend}/api/bridge/relay/ack",
                 {"job_id": job["id"], "status": "exception", "error": str(e)}, headers=headers)
            print(f"[ack] exception {job['id']}: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", required=True)
    ap.add_argument("--pair")
    ap.add_argument("--token")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=int(os.environ.get("ORDIA_BRIDGE_INTERVAL", "5")))
    args = ap.parse_args()

    token = args.token or (pair(args.backend, args.pair) if args.pair else load_token())
    if not token:
        print("No token. Pair first with --pair <CODE>.")
        sys.exit(1)

    config = load_config()
    print(f"[config] delivery_mode = {config.get('delivery_mode', 'file')}")

    if args.once:
        cycle(args.backend, token, config)
        return
    print(f"[run] Ordia Bridge agent polling every {args.interval}s (Ctrl+C to stop)")
    sync_state = {}
    _maybe_sync_catalog(args.backend, token, config, sync_state)  # sync once at startup if enabled
    while True:
        try:
            cycle(args.backend, token, config)
            _req("POST", f"{args.backend}/api/bridge/relay/heartbeat", {}, {"X-Bridge-Token": token})
            _maybe_sync_catalog(args.backend, token, config, sync_state)
        except Exception as e:
            print(f"[loop] error: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
