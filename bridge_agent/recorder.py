#!/usr/bin/env python3
"""Ordia Bridge — DESKTOP demonstration recorder (Windows).

Learn-by-demonstration for API-less / DOM-less desktop ERPs (Danea, Mexal,
TeamSystem desktop, ...). The operator creates ONE order by hand; this tool
watches via the Windows UI Automation (UIA) accessibility tree + input hooks,
records a deterministic TRACE (which control was used, what was typed), grabs a
few screenshots, and POSTs it to the cloud compiler
(`POST /api/bridge/adapters/compile`) which turns it into a replayable procedure.

The LLM/vision is used ONLY to compile (here) and to self-heal (replay_desktop.py),
never to click at runtime.

WINDOWS ONLY. Install:
    pip install pywinauto pynput mss pillow
Run (after the agent has been paired so .agent_state.json holds the token):
    python recorder.py --backend https://app.ordia.app --erp-key "danea/2024" --erp-guess "Danea Easyfatt"
Then: perform the order in the ERP. Press ESC to stop, compile and upload.
"""
import argparse
import base64
import io
import json
import os
import sys
import time
import urllib.request
import urllib.error

HERE = os.path.dirname(__file__)
STATE_FILE = os.environ.get("ORDIA_BRIDGE_STATE", os.path.join(HERE, ".agent_state.json"))

try:
    from pynput import mouse, keyboard
    from pywinauto import Desktop
    import mss
    from PIL import Image
except Exception as e:  # pragma: no cover - Windows-only deps
    print(f"[recorder] Windows deps mancanti ({e}). Installa: pip install pywinauto pynput mss pillow")
    sys.exit(2)


def _req(method, url, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json", "User-Agent": "OrdiaBridge/1.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def _load_token():
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE)).get("token")
    return None


class Recorder:
    """Captures clicks (with UIA element metadata) and typed text per focused control."""

    def __init__(self, max_shots=6):
        self.trace = []
        self.shots = []
        self.max_shots = max_shots
        self._type_buffer = ""
        self._last_elem = None
        self._desktop = Desktop(backend="uia")
        self._sct = mss.mss()

    def _elem_at(self, x, y):
        try:
            el = self._desktop.from_point(x, y).element_info
            top = self._desktop.top_from_point(x, y).window_text()
            return {"name": el.name or "", "automation_id": getattr(el, "automation_id", "") or "",
                    "control_type": el.control_type or "", "window_title": top or ""}
        except Exception:
            return {"name": "", "automation_id": "", "control_type": "", "window_title": ""}

    def _shot(self):
        if len(self.shots) >= self.max_shots:
            return
        try:
            raw = self._sct.grab(self._sct.monitors[1])
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            img.thumbnail((1280, 1280))
            buf = io.BytesIO(); img.save(buf, format="PNG")
            self.shots.append(base64.b64encode(buf.getvalue()).decode())
        except Exception:
            pass

    def _flush_typing(self):
        if self._type_buffer and self._last_elem:
            self.trace.append({"seq": len(self.trace) + 1, "action": "type",
                               "element": self._last_elem, "value": self._type_buffer})
            self._type_buffer = ""

    def on_click(self, x, y, button, pressed):
        if not pressed:
            return
        self._flush_typing()
        el = self._elem_at(x, y)
        self._last_elem = el
        self.trace.append({"seq": len(self.trace) + 1, "action": "click", "element": el, "value": None})
        self._shot()

    def on_press(self, key):
        if key == keyboard.Key.esc:
            return False  # stop listeners
        try:
            self._type_buffer += key.char
        except AttributeError:
            if key in (keyboard.Key.enter, keyboard.Key.tab):
                self._flush_typing()
                self.trace.append({"seq": len(self.trace) + 1, "action": "keypress",
                                   "element": self._last_elem, "value": str(key)})

    def run(self):
        print("[recorder] Registrazione avviata. Crea UN ordine nel gestionale. Premi ESC per terminare.")
        with mouse.Listener(on_click=self.on_click) as ml, \
             keyboard.Listener(on_press=self.on_press) as kl:
            kl.join()
            ml.stop()
        self._flush_typing()
        return self.trace, self.shots


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", required=True)
    ap.add_argument("--erp-key", required=True, help='es. "danea/2024"')
    ap.add_argument("--erp-guess", default="")
    args = ap.parse_args()

    token = _load_token()
    if not token:
        print("[recorder] Nessun token: accoppia prima l'agente (agent.py --pair <CODE>).")
        sys.exit(1)

    trace, shots = Recorder().run()
    print(f"[recorder] {len(trace)} azioni, {len(shots)} screenshot. Compilo la procedura…")
    status, data = _req("POST", f"{args.backend}/api/bridge/adapters/compile",
                        {"erp_key": args.erp_key, "erp_guess": args.erp_guess,
                         "trace": trace, "screenshots": shots},
                        {"X-Bridge-Token": token})
    if status == 200:
        print(f"[recorder] Adapter compilato: id={data.get('id')} v{data.get('version')} "
              f"kind={data.get('adapter_kind')} conf={data.get('confidence')} "
              f"passi={len((data.get('spec') or {}).get('steps', []))}")
        print("[recorder] Conferma l'ordine di prova in Ordia per attivarlo.")
    else:
        print(f"[recorder] Compilazione fallita HTTP {status}: {data}")


if __name__ == "__main__":
    main()
