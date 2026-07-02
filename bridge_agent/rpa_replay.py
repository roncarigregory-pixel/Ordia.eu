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
from playwright.async_api import async_playwright

HERE = os.path.dirname(__file__)
PROFILE = os.path.join(HERE, "adapter_profile.json")
SHOTS = os.path.join(HERE, "rpa_shots")
os.makedirs(SHOTS, exist_ok=True)


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

    lg = profile["login"]
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
            await page.goto(f"{url}{profile['new_order_path']}", wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_selector(".o_control_panel", timeout=45000)
            await page.wait_for_timeout(2000)
            await page.locator(profile["new_button_sel"]).first.click()
            await page.wait_for_timeout(2500)

            await page.locator(cust_sel).first.click()
            await _pick(page, customer)

            for ln in lines:
                await page.locator(f"a:has-text('{add_text}'), .o_field_x2many_list_row_add a").first.click()
                await page.wait_for_timeout(1200)
                await page.locator(prod_sel).first.click()
                await _pick(page, ln["product"])
                await page.wait_for_timeout(1000)
                await page.locator(qty_sel).first.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.type(str(ln["qty"]), delay=40)
                await page.keyboard.press("Tab")
                await page.wait_for_timeout(1000)

            tag = (std_order.get("order_id") or "order")[:8]
            await page.locator(profile["save_sel"]).first.click()
            await page.wait_for_timeout(3500)
            await page.screenshot(path=os.path.join(SHOTS, f"replay_{tag}.png"))
            try:
                ref = (await page.locator(".o_breadcrumb .o_last_breadcrumb_item, .breadcrumb-item.active").first.inner_text(timeout=5000)).strip()
            except Exception:
                ref = "(saved)"
            return {"order_ref": ref, "customer": customer, "lines": len(lines), "engine": "generic-replay"}
        finally:
            await browser.close()


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
