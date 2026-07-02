#!/usr/bin/env python3
"""Ordia Bridge — RPA-lite delivery (Class D / UI-only ERP).

Drives a REAL ERP web UI (Odoo) with mouse + keyboard via Playwright to CREATE an
order, operating the interface like a human. Exposed as deliver_via_rpa() so the
Bridge agent can use it as a delivery channel; also runnable standalone.
"""
import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

SHOTS = os.path.join(os.path.dirname(__file__), "rpa_shots")
os.makedirs(SHOTS, exist_ok=True)


def _map(value, mapping, default):
    return (mapping or {}).get(value, default or value)


async def _shot(page, name):
    try:
        await page.screenshot(path=os.path.join(SHOTS, name))
    except Exception:
        pass


async def _pick_autocomplete(page, value):
    await page.keyboard.type(value, delay=40)
    await page.wait_for_timeout(1200)
    option = page.locator(".o-autocomplete--dropdown-menu .o-autocomplete--dropdown-item, .ui-autocomplete li").first
    await option.wait_for(state="visible", timeout=8000)
    await option.click()
    await page.wait_for_timeout(800)


async def deliver_via_rpa(std_order: dict, config: dict) -> dict:
    """Create the order inside Odoo by driving its UI. Returns {order_ref, customer, lines}.
    Master-data mapping (canonical -> ERP names) is applied via config maps."""
    url = config.get("odoo_url", "http://localhost:8069")
    login = config.get("login", "admin")
    password = config.get("password", "admin")

    customer = _map((std_order.get("customer") or {}).get("name"),
                    config.get("customer_map"), config.get("default_customer", "Azure Interior"))
    lines = []
    for ln in std_order.get("lines", []):
        prod = _map(ln.get("product"), config.get("product_map"), config.get("default_product", "Storage Box"))
        qty = ln.get("quantity") or 1
        lines.append({"product": prod, "qty": qty, "source": ln.get("product")})
    if not lines:
        raise RuntimeError("Nessuna riga da consegnare")

    tag = (std_order.get("order_id") or "order")[:8]
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1600, "height": 1000})
        try:
            await page.goto(f"{url}/web/login", wait_until="domcontentloaded", timeout=45000)
            await page.fill('input[name="login"]', login)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"]')
            await page.wait_for_selector(".o_main_navbar", timeout=45000)

            await page.goto(f"{url}/odoo/sales", wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_selector(".o_control_panel", timeout=45000)
            await page.wait_for_timeout(2000)
            new_btn = page.locator("button.o_list_button_add, button.o-kanban-button-new, .o_control_panel button:has-text('New')").first
            await new_btn.click()
            await page.wait_for_timeout(2500)

            cust_input = page.locator('.o_field_widget[name="partner_id"] input').first
            await cust_input.click()
            await _pick_autocomplete(page, customer)

            for ln in lines:
                add_line = page.locator("a:has-text('Add a product'), .o_field_x2many_list_row_add a").first
                await add_line.click()
                await page.wait_for_timeout(1200)
                prod_input = page.locator('.o_selected_row .o_field_widget[name="product_template_id"] input, .o_selected_row .o_field_widget[name="product_id"] input').first
                await prod_input.click()
                await _pick_autocomplete(page, ln["product"])
                await page.wait_for_timeout(1200)
                qty_input = page.locator('.o_selected_row .o_field_widget[name="product_uom_qty"] input').first
                await qty_input.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.type(str(ln["qty"]), delay=40)
                await page.keyboard.press("Tab")
                await page.wait_for_timeout(1000)

            await _shot(page, f"rpa_{tag}_before_save.png")
            save_btn = page.locator("button.o_form_button_save, .o_form_button_save").first
            await save_btn.click()
            await page.wait_for_timeout(3500)
            await _shot(page, f"rpa_{tag}_saved.png")
            try:
                ref = (await page.locator(".o_breadcrumb .o_last_breadcrumb_item, .breadcrumb-item.active").first.inner_text(timeout=5000)).strip()
            except Exception:
                ref = "(saved)"
            return {"order_ref": ref, "customer": customer, "lines": len(lines),
                    "mapped": [(l["source"], l["product"], l["qty"]) for l in lines]}
        finally:
            await browser.close()


async def _main():
    order = {"customer": {"name": "Azure Interior"},
             "lines": [{"product": "Large Cabinet", "quantity": 2},
                       {"product": "Storage Box", "quantity": 5}]}
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        with open(sys.argv[1]) as f:
            order = json.load(f)
    cfg = {"odoo_url": os.environ.get("ODOO_URL", "http://localhost:8069"),
           "login": "admin", "password": "admin"}
    res = await deliver_via_rpa(order, cfg)
    print(f"[RESULT] {res}")


if __name__ == "__main__":
    asyncio.run(_main())
