#!/usr/bin/env python3
"""Ordia Bridge — LEARN a new ERP from a single demonstration/introspection.

Point the Bridge at an ERP's "new order" screen. It:
  1. Opens the form and INTROSPECTS every field (label + technical name + widget type).
  2. Sends that inventory to the LLM, which MAPS Ordia's canonical fields onto the
     ERP's fields and identifies the order-line controls.
  3. Saves a reusable "UI Adapter Profile" (adapter_profile.json).

Nothing about this specific ERP is hardcoded in the mapping: the field names are
DISCOVERED live and mapped by AI. rpa_replay.py then delivers orders using only
this profile — so a brand-new ERP is supported without writing new code.
"""
import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402

EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
OUT = os.path.join(os.path.dirname(__file__), "adapter_profile.json")
SHOTS = os.path.join(os.path.dirname(__file__), "rpa_shots")
os.makedirs(SHOTS, exist_ok=True)

LEARN_SYSTEM = """You are an ERP UI-integration analyst.
You receive an inventory of the fields found on an ERP "new sales order" screen:
each item has a visible LABEL, a technical field NAME, and a WIDGET type. You also
receive the list of order-line controls (e.g. an "add line" link) found on the page.

Map Ordia's canonical order onto this ERP form. Return ONLY valid JSON:
{
  "erp_guess": string,
  "customer_field": string,        // NAME of the field that holds the customer/partner
  "line_add_text": string,         // visible text of the control that adds an order line
  "product_field": string,         // NAME of the per-line product field
  "qty_field": string,             // NAME of the per-line quantity field
  "confidence": number,            // 0..1
  "notes": string
}
Choose NAMES strictly from the provided inventory. If unsure, pick the most likely."""


async def introspect(page):
    """Enumerate form fields (label + name + widget) and line controls."""
    fields = await page.eval_on_selector_all(
        ".o_field_widget[name]",
        """els => els.map(el => {
            const name = el.getAttribute('name');
            let label = '';
            const id = el.querySelector('input,textarea,select')?.id;
            if (id) { const l = document.querySelector(`label[for="${id}"]`); if (l) label = l.innerText.trim(); }
            if (!label) { const cell = el.closest('.o_cell'); }
            if (!label) { const lbl = el.closest('td,.o_wrap_field')?.parentElement?.querySelector('label,.o_form_label'); if (lbl) label = lbl.innerText.trim(); }
            const widget = el.classList.contains('o_field_many2one') ? 'autocomplete'
                         : (el.querySelector('input') ? 'input' : (el.querySelector('textarea') ? 'textarea' : 'other'));
            return {name, label, widget};
        })"""
    )
    line_controls = await page.eval_on_selector_all(
        ".o_field_x2many_list_row_add a, a:has-text('Add')",
        "els => els.map(e => e.innerText.trim()).filter(Boolean)"
    )
    # de-dup by name keeping first label
    seen, inv = set(), []
    for f in fields:
        if f["name"] and f["name"] not in seen:
            seen.add(f["name"]); inv.append(f)
    return inv, list(dict.fromkeys(line_controls))


async def main():
    url = os.environ.get("ODOO_URL", "http://localhost:8069")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1600, "height": 1000})
        try:
            await page.goto(f"{url}/web/login", wait_until="domcontentloaded", timeout=45000)
            await page.fill('input[name="login"]', "admin")
            await page.fill('input[name="password"]', "admin")
            await page.click('button[type="submit"]')
            await page.wait_for_selector(".o_main_navbar", timeout=45000)
            await page.goto(f"{url}/odoo/sales", wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_selector(".o_control_panel", timeout=45000)
            await page.wait_for_timeout(2000)
            await page.locator("button.o_list_button_add, .o_control_panel button:has-text('New')").first.click()
            await page.wait_for_timeout(2500)
            # reveal a line row so per-line fields exist in the DOM
            try:
                await page.locator("a:has-text('Add a product'), .o_field_x2many_list_row_add a").first.click()
                await page.wait_for_timeout(1500)
            except Exception:
                pass
            inv, line_controls = await introspect(page)
            await page.screenshot(path=os.path.join(SHOTS, "learn_form.png"))
        finally:
            await browser.close()

    print(f"[learn] discovered {len(inv)} fields; line controls: {line_controls}")
    inventory_text = json.dumps({"fields": inv, "line_controls": line_controls}, ensure_ascii=False)

    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id="erp-learn",
                   system_message=LEARN_SYSTEM).with_model("anthropic", "claude-sonnet-4-6")
    resp = await chat.send_message(UserMessage(text=f"FIELD INVENTORY:\n{inventory_text}\n\nReturn the mapping JSON."))
    text = resp.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip().rstrip("`").strip()
    profile = json.loads(text)
    profile["login"] = {"login_sel": 'input[name="login"]', "pass_sel": 'input[name="password"]',
                        "submit_sel": 'button[type="submit"]', "ready_sel": ".o_main_navbar"}
    profile["new_order_path"] = "/odoo/sales"
    profile["new_button_sel"] = "button.o_list_button_add, .o_control_panel button:has-text('New')"
    profile["save_sel"] = "button.o_form_button_save, .o_form_button_save"
    with open(OUT, "w") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    print(f"[learn] AI-derived adapter profile saved -> {OUT}")
    print(json.dumps({k: profile[k] for k in ("erp_guess", "customer_field", "line_add_text",
                                              "product_field", "qty_field", "confidence")}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
