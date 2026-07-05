#!/usr/bin/env python3
"""Ordia Bridge — native Windows agent (no Docker, no terminal for the end user).

One executable, two roles:
  * OrdiaBridge.exe            -> opens the friendly setup window (pairing GUI)
  * OrdiaBridge.exe run        -> background poll loop (started as a Windows service by WinSW)
  * OrdiaBridge.exe update     -> silent self-update check (run daily by the service)

Config lives in %PROGRAMDATA%\\OrdiaBridge\\config.json (created after pairing).
Only the Python standard library is used, so the packaged .exe stays small and dependency-free.
"""
import json
import os
import sys
import time
import ssl
import urllib.request
import urllib.error

# Baked-in default backend (overridable via env ORDIA_BACKEND). Production host.
DEFAULT_BACKEND = os.environ.get("ORDIA_BACKEND", "https://ordia.eu")
APP_VERSION = "1.0.0"
POLL_INTERVAL = int(os.environ.get("ORDIA_BRIDGE_INTERVAL", "5"))
UPDATE_CHECK_HOURS = 12

if os.name == "nt":
    DATA_DIR = os.path.join(os.environ.get("PROGRAMDATA", os.path.expanduser("~")), "OrdiaBridge")
else:
    DATA_DIR = os.environ.get("ORDIA_BRIDGE_DATA", os.path.join(os.path.dirname(__file__), ".ordia_data"))
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
LOG_FILE = os.path.join(DATA_DIR, "bridge.log")
OUT_DIR = os.path.join(DATA_DIR, "delivered")
_SSL = ssl.create_default_context()


# --------------------------------------------------------------------------- io
def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)


def log(msg):
    _ensure_dirs()
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    print(line)


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(cfg):
    _ensure_dirs()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def _req(method, url, body=None, headers=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json", "User-Agent": f"OrdiaBridge/{APP_VERSION}"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


# ------------------------------------------------------------------- pairing/api
def pair(backend, code):
    """Pair with a 6-digit code. Returns (ok, message)."""
    status, data = _req("POST", f"{backend}/api/bridge/pair", {"pairing_code": (code or "").strip()})
    if status != 200 or not data.get("token"):
        return False, data.get("detail") or "Codice non valido o già usato. Controlla e riprova."
    cfg = load_config()
    cfg.update({"backend": backend, "token": data["token"], "agent_id": data.get("agent_id"),
                "name": data.get("name"), "delivery_mode": cfg.get("delivery_mode", "file")})
    save_config(cfg)
    log(f"Paired as '{data.get('name')}' (agent {data.get('agent_id')})")
    return True, "Bridge collegato con successo."


def upload_logs(backend, token, consent=True):
    if not consent or not os.path.exists(LOG_FILE):
        return False
    try:
        with open(LOG_FILE, encoding="utf-8") as f:
            tail = f.readlines()[-500:]
        st, _ = _req("POST", f"{backend}/api/bridge/logs",
                     {"logs": "".join(tail), "version": APP_VERSION, "consent": True},
                     {"X-Bridge-Token": token})
        return st == 200
    except Exception:
        return False


def deliver(job):
    """Native MVP delivery: write the approved order to the local delivery folder.
    (ERP-specific automated delivery adapters are layered on later without changing this flow.)"""
    _ensure_dirs()
    ext = job.get("rendered_format") or "json"
    payload = job.get("rendered") or json.dumps(job.get("standard_order", {}), ensure_ascii=False, indent=2)
    path = os.path.join(OUT_DIR, f"order-{job['order_id'][:8]}.{ext}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(payload)
    return {"channel": "file", "delivered_to": path, "erp": job.get("erp_name")}


def cycle(backend, token):
    headers = {"X-Bridge-Token": token}
    status, data = _req("GET", f"{backend}/api/bridge/relay/poll", headers=headers)
    if status != 200:
        return
    for job in data.get("jobs", []):
        mode = job.get("mode", "live")
        try:
            result = {**deliver(job), "mode": mode}
            _req("POST", f"{backend}/api/bridge/relay/ack",
                 {"job_id": job["id"], "status": "delivered", "result": result}, headers=headers)
            log(f"Order {job['order_id'][:8]} delivered (mode={mode})")
        except Exception as e:
            _req("POST", f"{backend}/api/bridge/relay/ack",
                 {"job_id": job["id"], "status": "exception", "error": str(e)}, headers=headers)
            log(f"Delivery error {job['id']}: {e}")


def check_update(backend):
    """Best-effort silent auto-update: download & run the newer installer silently."""
    st, data = _req("GET", f"{backend}/api/bridge/installer/windows")
    if st != 200 or not data.get("available"):
        return
    latest = data.get("version") or ""
    if latest and latest > APP_VERSION and data.get("url"):
        try:
            tmp = os.path.join(DATA_DIR, "OrdiaBridgeSetup_update.exe")
            urllib.request.urlretrieve(data["url"], tmp)
            log(f"Downloaded update {latest}, launching silent installer")
            os.startfile(tmp) if hasattr(os, "startfile") else None  # /VERYSILENT handled by installer
        except Exception as e:
            log(f"Update check failed: {e}")


def run_loop():
    cfg = load_config()
    backend, token = cfg.get("backend", DEFAULT_BACKEND), cfg.get("token")
    if not token:
        log("Not paired yet — waiting for setup. Open 'Ordia Bridge' from the Start menu.")
        while not token:
            time.sleep(15)
            cfg = load_config()
            token = cfg.get("token")
            backend = cfg.get("backend", DEFAULT_BACKEND)
    log(f"Ordia Bridge running (v{APP_VERSION}), polling {backend}")
    last_update = last_log = 0.0
    while True:
        try:
            cycle(backend, token)
            _req("POST", f"{backend}/api/bridge/relay/heartbeat", {}, {"X-Bridge-Token": token})
            now = time.time()
            if now - last_update > UPDATE_CHECK_HOURS * 3600:
                check_update(backend); last_update = now
            if now - last_log > 3600 and cfg.get("log_consent", True):
                upload_logs(backend, token, True); last_log = now
        except Exception as e:
            log(f"Loop error: {e}")
        time.sleep(POLL_INTERVAL)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "configure"
    if cmd == "run":
        run_loop()
    elif cmd == "update":
        check_update(load_config().get("backend", DEFAULT_BACKEND))
    else:
        from config_gui import launch_gui
        launch_gui()


if __name__ == "__main__":
    main()
