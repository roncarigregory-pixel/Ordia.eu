#!/usr/bin/env python3
"""Ordia Bridge — DESKTOP deterministic replayer (Windows, UIA).

Delivers a canonical order into an API-less/DOM-less desktop ERP by REPLAYING a
learned `desktop_adapter_spec` (compiled by the cloud from a demonstration).

Design principle: the LLM/vision NEVER clicks at runtime. Replay is deterministic
against semantic locators. Locator robustness order:
    automation_id  ->  name  ->  text_anchor (OCR)  ->  bbox (vision)
Absolute pixels are never used. Vision/OCR run ONLY when a locator fails (self-heal).

Flow: resolve active desktop_uia adapter -> pre-flight window fingerprint -> run
steps (with per-order-line loop) -> save -> report success/failure. On a failed
locator, re-introspect the current window, ask the cloud compiler to re-locate,
PUT /heal the patched spec, retry once.

WINDOWS ONLY. Install:
    pip install pywinauto mss pillow pytesseract   # pytesseract optional (OCR anchor)
Usage (called by agent.py in delivery_mode=desktop_uia, or standalone):
    python replay_desktop.py order.json --backend https://app.ordia.app --erp-key "danea/2024"
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

HERE = os.path.dirname(__file__)
STATE_FILE = os.environ.get("ORDIA_BRIDGE_STATE", os.path.join(HERE, ".agent_state.json"))
CONFIG_FILE = os.environ.get("ORDIA_BRIDGE_CONFIG", os.path.join(HERE, "config.json"))


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
    return json.load(open(STATE_FILE)).get("token") if os.path.exists(STATE_FILE) else None


class DesktopReplayError(Exception):
    pass


class PreflightMismatch(DesktopReplayError):
    """Live window does not match the learned fingerprint — refuse to type."""


try:
    from pywinauto import Desktop, Application  # noqa: F401
    _HAS_UIA = True
except Exception:  # pragma: no cover - Windows-only
    _HAS_UIA = False


class DesktopDriver:
    """Thin UIA driver. Locates controls by the spec's locator hierarchy."""

    def __init__(self, cfg):
        if not _HAS_UIA:
            raise DesktopReplayError("pywinauto non disponibile: esegui su Windows con `pip install pywinauto`.")
        self.cfg = cfg
        self.desktop = Desktop(backend="uia")
        self.win = None

    def attach_window(self, title_regex):
        self.win = self.desktop.window(title_re=title_regex or ".*")
        self.win.wait("exists ready", timeout=30)
        return self.win

    def preflight(self, window_spec):
        title_re = (window_spec or {}).get("title_regex", ".*")
        self.attach_window(title_re)
        needed = set((window_spec or {}).get("fingerprint_controls", []))
        if not needed:
            return
        present = set()
        for d in self.win.descendants():
            aid = getattr(d.element_info, "automation_id", "") or ""
            if aid:
                present.add(aid)
        overlap = len(needed & present) / len(needed) if needed else 1.0
        if overlap < 0.6:
            raise PreflightMismatch(f"impronta finestra cambiata (overlap {int(overlap*100)}%)")

    def _find(self, locator):
        by, val = locator.get("by"), locator.get("value")
        ct = locator.get("control_type") or None
        # 1) automation_id  2) name  (semantic, robust)
        try:
            if by == "automation_id":
                return self.win.child_window(auto_id=val, control_type=ct)
            if by == "name":
                return self.win.child_window(title=val, control_type=ct)
        except Exception:
            pass
        # 3) text_anchor (OCR) / 4) bbox (vision) are handled by self-heal upstream
        raise DesktopReplayError(f"locator non risolto: {locator}")

    def set_field(self, locator, value):
        ctrl = self._find(locator)
        ctrl.wait("exists ready", timeout=8)
        try:
            ctrl.set_edit_text(str(value))
        except Exception:
            ctrl.click_input(); ctrl.type_keys("^a{DEL}", pause=0.02); ctrl.type_keys(str(value), with_spaces=True)
        time.sleep(0.2)

    def click(self, locator):
        ctrl = self._find(locator)
        ctrl.wait("exists ready", timeout=8)
        ctrl.click_input()
        time.sleep(0.3)


def _canonical_value(std, field):
    if field == "customer_name":
        return (std.get("customer") or {}).get("name")
    return None  # line-scoped fields resolved during the loop


def replay(spec, std_order, cfg):
    drv = DesktopDriver(cfg)
    drv.preflight(spec.get("window"))
    steps = sorted(spec.get("steps", []), key=lambda s: s.get("seq", 0))
    loop = spec.get("line_loop")
    lines = std_order.get("lines", [])

    def run_step(step, line=None):
        op = step.get("op")
        if op in ("open_form", "click", "save", "select"):
            drv.click(step["locator"])
        elif op == "set_field":
            field = step.get("field")
            if line is not None and field in ("sku", "product", "quantity"):
                val = line.get("product") if field in ("sku", "product") else line.get("quantity")
            else:
                val = _canonical_value(std_order, field)
            if val is not None:
                drv.set_field(step["locator"], val)
        elif op == "wait":
            time.sleep(1.0)

    if loop:
        pre = [s for s in steps if s["seq"] < loop["start_seq"]]
        body = [s for s in steps if loop["start_seq"] <= s["seq"] <= loop["end_seq"]]
        post = [s for s in steps if s["seq"] > loop["end_seq"]]
        for s in pre:
            run_step(s)
        for ln in lines:
            for s in body:
                run_step(s, line=ln)
        for s in post:
            run_step(s)
    else:
        for s in steps:
            run_step(s)
    return {"engine": "desktop-uia", "lines": len(lines)}


def replay_with_healing(spec, std_order, cfg, backend=None, token=None, adapter_id=None):
    """Deterministic replay; on a locator/preflight failure, re-introspect the live
    window, ask the cloud compiler to re-locate, PUT /heal the patched spec, retry once."""
    try:
        return replay(spec, std_order, cfg)
    except Exception as e:
        print(f"[self-heal] replay desktop fallito ({type(e).__name__}: {str(e)[:90]}). Riapprendo la finestra…")
        if not (backend and token and adapter_id):
            raise
        trace = _introspect_current_window(spec)
        st, data = _req("POST", f"{backend}/api/bridge/adapters/compile",
                        {"erp_key": spec.get("_erp_key", ""), "erp_guess": spec.get("erp_guess", ""),
                         "trace": trace}, {"X-Bridge-Token": token})
        if st != 200:
            raise DesktopReplayError(f"self-heal compile fallita HTTP {st}")
        healed = data.get("spec") or {}
        _req("PUT", f"{backend}/api/bridge/adapters/{adapter_id}/heal",
             {"erp_key": spec.get("_erp_key", ""), "spec": healed,
              "confidence": healed.get("confidence", 0)}, {"X-Bridge-Token": token})
        print("[self-heal] spec riparata e ripubblicata; riprovo una volta.")
        return replay(healed, std_order, cfg)


def _introspect_current_window(spec):
    """Snapshot the current window's controls as a minimal trace for the compiler."""
    if not _HAS_UIA:
        return []
    desktop = Desktop(backend="uia")
    win = desktop.window(title_re=(spec.get("window") or {}).get("title_regex", ".*"))
    trace = []
    for i, d in enumerate(win.descendants()):
        ei = d.element_info
        trace.append({"seq": i + 1, "action": "inventory",
                      "element": {"name": ei.name or "",
                                  "automation_id": getattr(ei, "automation_id", "") or "",
                                  "control_type": ei.control_type or "",
                                  "window_title": win.window_text()}, "value": None})
    return trace


async def deliver_via_desktop(std_order, cfg, backend=None, token=None):
    """Entry point used by agent.py (delivery_mode='desktop_uia')."""
    erp_key = cfg.get("erp_key", "")
    st, adapter = _req("GET",
        f"{backend}/api/bridge/adapters/resolve?erp_key={erp_key}&adapter_kind=desktop_uia",
        headers={"X-Bridge-Token": token})
    if st != 200:
        raise DesktopReplayError(f"Nessun adapter desktop attivo per {erp_key} (HTTP {st}) — apprendi e conferma prima")
    spec = adapter["spec"]; spec["_erp_key"] = erp_key
    adapter_id = adapter["id"]
    try:
        res = replay_with_healing(spec, std_order, cfg, backend, token, adapter_id)
        _req("POST", f"{backend}/api/bridge/adapters/{adapter_id}/report", {"status": "success"},
             {"X-Bridge-Token": token})
        return {"channel": "desktop_uia", "adapter_version": adapter.get("version"), **res}
    except Exception:
        _req("POST", f"{backend}/api/bridge/adapters/{adapter_id}/report", {"status": "failure"},
             {"X-Bridge-Token": token})
        raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("order", nargs="?", help="JSON file con l'ordine canonico")
    ap.add_argument("--backend", required=True)
    ap.add_argument("--erp-key", required=True)
    args = ap.parse_args()
    cfg = json.load(open(CONFIG_FILE)) if os.path.exists(CONFIG_FILE) else {}
    cfg["erp_key"] = args.erp_key
    order = {"customer": {"name": "Cliente Prova"}, "lines": [{"product": "Articolo A", "quantity": 2}]}
    if args.order and os.path.exists(args.order):
        order = json.load(open(args.order))
    import asyncio
    print(json.dumps(asyncio.run(deliver_via_desktop(order, cfg, args.backend, _load_token())), ensure_ascii=False))


if __name__ == "__main__":
    main()
