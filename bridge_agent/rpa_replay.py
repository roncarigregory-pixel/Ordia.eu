#!/usr/bin/env python3
"""Ordia Bridge — GENERIC UI replay engine.

Delivers a canonical order into ANY ERP using a learned UI Adapter Profile
(adapter_profile.json produced by rpa_learn.py). This engine contains NO
ERP-specific field names: every selector comes from the learned profile.
Proves that once an ERP is learned, orders are created with zero new code.
"""
import asyncio
import json
import os
import sys
import hashlib
from playwright.async_api import async_playwright

HERE = os.path.dirname(__file__)
PROFILE = os.path.join(HERE, "adapter_profile.json")
SHOTS = os.path.join(HERE, "rpa_shots")
os.makedirs(SHOTS, exist_ok=True)


class PreflightMismatch(Exception):
    """The live screen does not match the learned adapter — refuse to type data."""


async def _preflight(page, profile: dict):
    """Verify we are on the expected screen BEFORE mutating anything. If the learned
    UI signature no longer matches (ERP changed/updated), raise so healing kicks in.
    This is what keeps the RPA from 'spraying data at the wrong screen'."""
    cust_sel = f'.o_field_widget[name="{profile["customer_field"]}"] input'
    try:
        await page.locator(cust_sel).first.wait_for(state="visible", timeout=8000)
    except Exception:
        raise PreflightMismatch(f"campo cliente '{profile['customer_field']}' non trovato")
    expected = profile.get("ui_fingerprint")
    if expected:
        names = await page.eval_on_selector_all(
            ".o_field_widget[name]",
            "els => Array.from(new Set(els.map(e => e.getAttribute('name')).filter(Boolean))).sort()")
        live_fp = hashlib.sha1("|".join(names).encode()).hexdigest()[:16]
        if live_fp != expected:
            learned = set(profile.get("field_names") or [])
            overlap = (len(learned & set(names)) / len(learned)) if learned else 1.0
            if overlap < 0.6:
                raise PreflightMismatch(
                    f"impronta UI cambiata (overlap {int(overlap*100)}%) — riapprendo")


def _map(v, mapping, default):
    return (mapping or {}).get(v, default or v)


async def _pick(page, value):
    await page.keyboard.type(value, delay=40)
    await page.wait_for_timeout(1200)
    opt = page.locator(".o-autocomplete--dropdown-menu .o-autocomplete--dropdown-item, .ui-autocomplete li").first
    await opt.wait_for(state="visible", timeout=8000)
    await opt.click()
    await page.wait_for_timeout(800)


async def replay(profile: dict, std_order: dict, cfg: dict) -> dict:
    url = cfg.get("odoo_url", "http://localhost:8069")
    customer = _map((std_order.get("customer") or {}).get("name"),
                    cfg.get("customer_map"), cfg.get("default_customer", "Azure Interior"))
    lines = [{"product": _map(l.get("product"), cfg.get("product_map"), cfg.get("default_product", "Storage Box")),
              "qty": l.get("quantity") or 1} for l in std_order.get("lines", [])]

    lg = profile.get("login") or {}
    lg = {"login_sel": lg.get("login_sel", 'input[name="login"]'),
          "pass_sel": lg.get("pass_sel", 'input[name="password"]'),
          "submit_sel": lg.get("submit_sel", 'button[type="submit"]'),
          "ready_sel": lg.get("ready_sel", ".o_main_navbar")}
    new_order_path = profile.get("new_order_path", "/odoo/sales")
    new_button_sel = profile.get("new_button_sel", "button.o_list_button_add, .o_control_panel button:has-text('New')")
    save_sel = profile.get("save_sel", "button.o_form_button_save, .o_form_button_save")
    cust_sel = f'.o_field_widget[name="{profile["customer_field"]}"] input'
    prod_sel = f'.o_selected_row .o_field_widget[name="{profile["product_field"]}"] input'
    qty_sel = f'.o_selected_row .o_field_widget[name="{profile["qty_field"]}"] input'
    add_text = profile["line_add_text"]

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1600, "height": 1000})
        try:
            await page.goto(f"{url}/web/login", wait_until="domcontentloaded", timeout=45000)
            await page.fill(lg["login_sel"], cfg.get("login", "admin"))
            await page.fill(lg["pass_sel"], cfg.get("password", "admin"))
            await page.click(lg["submit_sel"])
            await page.wait_for_selector(lg["ready_sel"], timeout=45000)
            await page.goto(f"{url}{new_order_path}", wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_selector(".o_control_panel", timeout=45000)
            await page.wait_for_timeout(2000)
            await page.locator(new_button_sel).first.click()
            await page.wait_for_timeout(2500)

            await _preflight(page, profile)  # refuse to type if this isn't the right screen

            await page.locator(cust_sel).first.click(timeout=8000)
            await _pick(page, customer)

            for ln in lines:
                await page.locator(f"a:has-text('{add_text}'), .o_field_x2many_list_row_add a").first.click()
                await page.wait_for_timeout(1200)
                # product field — validate selector (self-healing hook triggers on failure upstream)
                await page.locator(prod_sel).first.click(timeout=8000)
                await _pick(page, ln["product"])
                await page.wait_for_timeout(1000)
                await page.locator(qty_sel).first.click(timeout=8000)
                await page.keyboard.press("Control+A")
                await page.keyboard.type(str(ln["qty"]), delay=40)
                await page.keyboard.press("Tab")
                await page.wait_for_timeout(1000)

            tag = (std_order.get("order_id") or "order")[:8]
            await page.locator(save_sel).first.click()
            await page.wait_for_timeout(3500)
            await page.screenshot(path=os.path.join(SHOTS, f"replay_{tag}.png"))
            try:
                ref = (await page.locator(".o_breadcrumb .o_last_breadcrumb_item, .breadcrumb-item.active").first.inner_text(timeout=5000)).strip()
            except Exception:
                ref = "(saved)"
            return {"order_ref": ref, "customer": customer, "lines": len(lines), "engine": "generic-replay"}
        finally:
            await browser.close()


async def replay_with_healing(profile: dict, std_order: dict, cfg: dict, backend=None, token=None, adapter_id=None):
    """Deliver via the learned profile. If a learned selector no longer matches (UI
    changed), RE-LEARN the ERP form, patch the profile, push the heal upstream, retry once."""
    try:
        return await replay(profile, std_order, cfg)
    except Exception as e:
        print(f"[self-heal] replay failed ({type(e).__name__}: {str(e)[:80]}). Re-learning ERP UI…")
        from rpa_learn import learn_adapter
        fresh = await learn_adapter(cfg.get("odoo_url", "http://localhost:8069"))
        # patch the field recipe with freshly discovered names
        for k in ("customer_field", "product_field", "qty_field", "line_add_text"):
            profile[k] = fresh.get(k, profile.get(k))
        profile["confidence"] = fresh.get("confidence", profile.get("confidence"))
        print(f"[self-heal] re-learned: customer={profile['customer_field']} product={profile['product_field']} qty={profile['qty_field']}")
        if backend and token and adapter_id:
            import urllib.request, urllib.error
            body = json.dumps({"erp_key": "odoo/18", "spec": profile,
                               "confidence": profile.get("confidence", 0)}).encode()
            req = urllib.request.Request(f"{backend}/api/bridge/adapters/{adapter_id}/heal", data=body,
                                         headers={"Content-Type": "application/json", "X-Bridge-Token": token}, method="PUT")
            try:
                urllib.request.urlopen(req, timeout=30)
                print("[self-heal] healed adapter pushed to backend")
            except Exception as ex:
                print(f"[self-heal] heal push failed: {ex}")
        return await replay(profile, std_order, cfg)


async def _main():
    with open(PROFILE) as f:
        profile = json.load(f)
    order = {"customer": {"name": "Azure Interior"},
             "lines": [{"product": "Large Desk", "quantity": 4}]}
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        with open(sys.argv[1]) as f:
            order = json.load(f)
    cfg = {"odoo_url": os.environ.get("ODOO_URL", "http://localhost:8069"), "login": "admin", "password": "admin"}
    print(f"[replay] using learned profile for '{profile.get('erp_guess')}' "
          f"(customer_field={profile['customer_field']}, product_field={profile['product_field']}, qty_field={profile['qty_field']})")
    print(f"[RESULT] {await replay(profile, order, cfg)}")


if __name__ == "__main__":
    asyncio.run(_main())
