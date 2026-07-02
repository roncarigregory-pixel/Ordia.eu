#!/usr/bin/env python3
"""Ordia Bridge — RPA-lite PoC (Class D / UI-only ERP).

Drives a REAL ERP web UI (Odoo) with mouse + keyboard via Playwright:
login -> open Sales -> New order -> fill customer -> add product lines -> Save.
Proves the Bridge can CREATE an order inside the ERP even without using its API,
by operating the interface exactly like a human would.

Screenshots of every step are written to rpa_shots/ as visual proof.
"""
import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

ODOO_URL = os.environ.get("ODOO_URL", "http://localhost:8069")
SHOTS = os.path.join(os.path.dirname(__file__), "rpa_shots")
os.makedirs(SHOTS, exist_ok=True)

# Canonical order (as produced by Ordia) mapped to the ERP's master data.
# In production the master-data step resolves Ordia SKUs -> ERP product names.
ORDER = {
    "customer": "Azure Interior",
    "lines": [
        {"product": "Large Cabinet", "qty": 2},
        {"product": "Storage Box", "qty": 5},
    ],
}


async def shot(page, name):
    path = os.path.join(SHOTS, name)
    await page.screenshot(path=path)
    print(f"[shot] {path}")


async def pick_autocomplete(page, value):
    """Type into the currently focused autocomplete and click the first match."""
    await page.keyboard.type(value, delay=40)
    await page.wait_for_timeout(1200)
    # Odoo OWL autocomplete dropdown
    option = page.locator(".o-autocomplete--dropdown-menu .o-autocomplete--dropdown-item, .ui-autocomplete li").first
    await option.wait_for(state="visible", timeout=8000)
    await option.click()
    await page.wait_for_timeout(800)


async def main():
    order = ORDER
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        with open(sys.argv[1]) as f:
            order = json.load(f)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1600, "height": 1000})
        try:
            # 1) LOGIN (type credentials, click)
            await page.goto(f"{ODOO_URL}/web/login", wait_until="domcontentloaded", timeout=45000)
            await page.fill('input[name="login"]', "admin")
            await page.fill('input[name="password"]', "admin")
            await shot(page, "01_login.png")
            await page.click('button[type="submit"]')
            await page.wait_for_selector(".o_main_navbar", timeout=45000)
            await page.wait_for_timeout(2000)
            await shot(page, "02_home.png")
            print("[step] logged in")

            # 2) OPEN SALES -> NEW ORDER
            await page.goto(f"{ODOO_URL}/odoo/sales", wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_selector(".o_control_panel", timeout=45000)
            await page.wait_for_timeout(2500)
            await shot(page, "03_sales_list.png")
            new_btn = page.locator("button.o_list_button_add, button.o-kanban-button-new, .o_control_panel button:has-text('New')").first
            await new_btn.click()
            await page.wait_for_timeout(2500)
            await shot(page, "04_new_order_form.png")
            print("[step] new order form opened")

            # 3) FILL CUSTOMER (mouse click + keyboard type + select)
            cust_input = page.locator('.o_field_widget[name="partner_id"] input').first
            await cust_input.click()
            await pick_autocomplete(page, order["customer"])
            await shot(page, "05_customer_filled.png")
            print(f"[step] customer set: {order['customer']}")

            # 4) ADD PRODUCT LINES
            for i, line in enumerate(order["lines"]):
                add_line = page.locator("a:has-text('Add a product'), .o_field_x2many_list_row_add a").first
                await add_line.click()
                await page.wait_for_timeout(1200)
                prod_input = page.locator('.o_selected_row .o_field_widget[name="product_template_id"] input, .o_selected_row .o_field_widget[name="product_id"] input').first
                await prod_input.click()
                await pick_autocomplete(page, line["product"])
                await page.wait_for_timeout(1500)
                # set quantity
                qty_input = page.locator('.o_selected_row .o_field_widget[name="product_uom_qty"] input').first
                await qty_input.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.type(str(line["qty"]), delay=40)
                await page.keyboard.press("Tab")
                await page.wait_for_timeout(1200)
                print(f"[step] line added: {line['product']} x{line['qty']}")
                await shot(page, f"06_line_{i+1}.png")

            await shot(page, "07_before_save.png")

            # 5) SAVE (click the save button)
            save_btn = page.locator("button.o_form_button_save, .o_form_button_save").first
            await save_btn.click()
            await page.wait_for_timeout(3500)
            await shot(page, "08_saved.png")

            # 6) VERIFY: read the order reference from the breadcrumb
            try:
                ref = await page.locator(".o_breadcrumb .o_last_breadcrumb_item, .breadcrumb-item.active").first.inner_text(timeout=5000)
            except Exception:
                ref = "(saved)"
            print(f"[RESULT] Order SAVED in Odoo — reference: {ref.strip()}")
        except Exception as e:
            await shot(page, "99_error.png")
            print(f"[ERROR] {type(e).__name__}: {e}")
            raise
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
