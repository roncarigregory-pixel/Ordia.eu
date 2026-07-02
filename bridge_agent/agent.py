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


def deliver(job):
    """Simulate delivery into the ERP. Real agents: call local ERP API / drop import
    file / RPA-lite. Here we just persist the rendered payload and report success."""
    os.makedirs(OUT_DIR, exist_ok=True)
    ext = job.get("rendered_format") or "json"
    payload = job.get("rendered") or json.dumps(job.get("standard_order", {}), ensure_ascii=False, indent=2)
    path = os.path.join(OUT_DIR, f"order-{job['order_id'][:8]}.{ext}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(payload)
    print(f"[deliver] order {job['order_id'][:8]} -> {path}")
    return {"delivered_to": path, "erp": job.get("erp_name")}


def cycle(backend, token):
    headers = {"X-Bridge-Token": token}
    status, data = _req("GET", f"{backend}/api/bridge/relay/poll", headers=headers)
    if status != 200:
        print(f"[poll] {status}: {data}")
        return
    jobs = data.get("jobs", [])
    if jobs:
        print(f"[poll] {len(jobs)} job(s) claimed")
    for job in jobs:
        try:
            result = deliver(job)
            _req("POST", f"{backend}/api/bridge/relay/ack",
                 {"job_id": job["id"], "status": "delivered", "result": result}, headers=headers)
            print(f"[ack] delivered {job['id']}")
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

    if args.once:
        cycle(args.backend, token)
        return
    print(f"[run] Ordia Bridge agent polling every {args.interval}s (Ctrl+C to stop)")
    while True:
        try:
            cycle(args.backend, token)
            _req("POST", f"{args.backend}/api/bridge/relay/heartbeat", {}, {"X-Bridge-Token": token})
        except Exception as e:
            print(f"[loop] error: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
