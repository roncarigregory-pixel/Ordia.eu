#!/usr/bin/env python3
"""Ordia Bridge — LEARN a new ERP (introspection + AI mapping), reusable.

learn_adapter(url) -> spec dict (login/new-order selectors + AI-mapped field names).
Standalone run: learn -> create a TEST order -> push adapter (pending_confirmation)
to the backend so a human can confirm the test order before go-live.
"""
import asyncio
import json
import os
import sys
import hashlib
import urllib.request
import urllib.error
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402

EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "adapter_profile.json")
SHOTS = os.path.join(HERE, "rpa_shots")
STATE_FILE = os.path.join(HERE, ".agent_state.json")
os.makedirs(SHOTS, exist_ok=True)

LEARN_SYSTEM = """You are an ERP UI-integration analyst.
You receive an inventory of fields on an ERP "new sales order" screen (each with a
visible LABEL, a technical field NAME, a WIDGET type) and the order-line controls.
Map Ordia's canonical order onto this form. Return ONLY valid JSON:
{"erp_guess": string, "customer_field": string, "line_add_text": string,
 "product_field": string, "qty_field": string, "confidence": number, "notes": string}
Choose NAMES strictly from the inventory."""


async def _introspect(page):
    fields = await page.eval_on_selector_all(
        ".o_field_widget[name]",
        """els => els.map(el => {
            const name = el.getAttribute('name');
            let label = '';
            const id = el.querySelector('input,textarea,select')?.id;
            if (id) { const l = document.querySelector(`label[for="${id}"]`); if (l) label = l.innerText.trim(); }
            if (!label) { const lbl = el.closest('td,.o_wrap_field')?.parentElement?.querySelector('label,.o_form_label'); if (lbl) label = lbl.innerText.trim(); }
            const widget = el.classList.contains('o_field_many2one') ? 'autocomplete' : (el.querySelector('input') ? 'input' : 'other');
            return {name, label, widget};
        })""")
    line_controls = await page.eval_on_selector_all(
        ".o_field_x2many_list_row_add a, a:has-text('Add')",
        "els => els.map(e => e.innerText.trim()).filter(Boolean)")
    seen, inv = set(), []
    for f in fields:
        if f["name"] and f["name"] not in seen:
            seen.add(f["name"]); inv.append(f)
    return inv, list(dict.fromkeys(line_controls))


async def learn_adapter(url):
    """Open the ERP new-order form, introspect fields, AI-map to canonical. Returns spec."""
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
            try:
                await page.locator("a:has-text('Add a product'), .o_field_x2many_list_row_add a").first.click()
                await page.wait_for_timeout(1500)
            except Exception:
                pass
            inv, line_controls = await _introspect(page)
            await page.screenshot(path=os.path.join(SHOTS, "learn_form.png"))
        finally:
            await browser.close()

    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id="erp-learn",
                   system_message=LEARN_SYSTEM).with_model("anthropic", "claude-sonnet-4-6")
    resp = await chat.send_message(UserMessage(
        text=f"FIELD INVENTORY:\n{json.dumps({'fields': inv, 'line_controls': line_controls}, ensure_ascii=False)}\n\nReturn the mapping JSON."))
    text = resp.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        text = text[4:] if text.startswith("json") else text
        text = text.strip().rstrip("`").strip()
    m = json.loads(text)
    m["login"] = {"login_sel": 'input[name="login"]', "pass_sel": 'input[name="password"]',
                  "submit_sel": 'button[type="submit"]', "ready_sel": ".o_main_navbar"}
    m["new_order_path"] = "/odoo/sales"
    m["new_button_sel"] = "button.o_list_button_add, .o_control_panel button:has-text('New')"
    m["save_sel"] = "button.o_form_button_save, .o_form_button_save"
    m["_discovered_fields"] = len(inv)
    # UI fingerprint: a stable signature of the form's field names so the replay
    # engine can PRE-FLIGHT verify it is on the right screen before typing anything.
    names = sorted([f["name"] for f in inv if f.get("name")])
    m["field_names"] = names
    m["ui_fingerprint"] = hashlib.sha1("|".join(names).encode()).hexdigest()[:16]
    return m


def _req(method, url, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json", "User-Agent": "OrdiaBridge/1.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


async def _main():
    url = os.environ.get("ODOO_URL", "http://localhost:8069")
    backend = sys.argv[1] if len(sys.argv) > 1 else None
    spec = await learn_adapter(url)
    with open(OUT, "w") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    print(f"[learn] discovered {spec['_discovered_fields']} fields; AI map: "
          f"customer={spec['customer_field']} product={spec['product_field']} qty={spec['qty_field']} conf={spec['confidence']}")

    # create a TEST order using the learned profile (human will confirm it)
    test_ref = None
    try:
        from rpa_replay import replay
        cfg = {"odoo_url": url, "login": "admin", "password": "admin",
               "default_customer": "Azure Interior", "default_product": "Storage Box"}
        test_order = {"order_id": "TESTLEARN", "customer": {"name": "Azure Interior"},
                      "lines": [{"product": "Storage Box", "quantity": 1}]}
        res = await replay(spec, test_order, cfg)
        test_ref = res.get("order_ref")
        print(f"[learn] test order created: {test_ref}")
    except Exception as e:
        print(f"[learn] test order failed: {e}")

    if backend and os.path.exists(STATE_FILE):
        token = json.load(open(STATE_FILE)).get("token")
        st, data = _req("POST", f"{backend}/api/bridge/adapters",
                        {"erp_key": "odoo/18", "erp_guess": spec.get("erp_guess", ""),
                         "spec": spec, "confidence": spec.get("confidence", 0), "test_order_ref": test_ref},
                        {"X-Bridge-Token": token})
        print(f"[learn] adapter pushed to backend: HTTP {st} id={data.get('id')} status={data.get('status')}")


if __name__ == "__main__":
    asyncio.run(_main())
