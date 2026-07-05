#!/usr/bin/env python3
"""Ordia Bridge — master-data + catalog sync.

Imports the ERP's code lists (customers, products, tax) from Odoo and pushes them to
the Ordia backend. Product entries carry price + unit so the Ordia catalog can
auto-sync from the ERP (canonical->ERP mapping still resolves to REAL codes).
Runs on-prem in the agent (has ERP access); credentials never leave the premises.
"""
import json
import os
import sys
import urllib.request
import urllib.error

HERE = os.path.dirname(__file__)
STATE_FILE = os.path.join(HERE, ".agent_state.json")
ODOO_URL = os.environ.get("ODOO_URL", "http://localhost:8069")
DB = os.environ.get("ODOO_DB", "ordia")
ODOO_LOGIN = os.environ.get("ODOO_LOGIN", "admin")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "admin")


def rpc(service, method, args):
    payload = {"jsonrpc": "2.0", "method": "call", "params": {"service": service, "method": method, "args": args}}
    req = urllib.request.Request(ODOO_URL + "/jsonrpc", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "OrdiaBridge/1.0"})
    return json.load(urllib.request.urlopen(req, timeout=60)).get("result")


def push(backend, token, erp_key, kind, entries):
    body = json.dumps({"erp_key": erp_key, "kind": kind, "entries": entries}).encode()
    req = urllib.request.Request(f"{backend}/api/bridge/master-data", data=body,
                                 headers={"Content-Type": "application/json", "X-Bridge-Token": token, "User-Agent": "OrdiaBridge/1.0"},
                                 method="POST")
    return json.load(urllib.request.urlopen(req, timeout=45))


def _uom_name(v):
    return v[1] if isinstance(v, (list, tuple)) and len(v) > 1 else ""


def run_sync(backend, token):
    """Pull customers/products/tax from Odoo and push to Ordia. Returns per-kind counts."""
    uid = rpc("common", "authenticate", [DB, ODOO_LOGIN, ODOO_PASSWORD, {}])

    def read(model, domain, fields):
        return rpc("object", "execute_kw", [DB, uid, ODOO_PASSWORD, model, "search_read", [domain], {"fields": fields, "limit": 1000}])

    customers = [{"erp_id": p["id"], "code": p.get("ref") or "", "name": p["name"]}
                 for p in read("res.partner", [["customer_rank", ">", 0]], ["name", "ref"])]
    products = [{"erp_id": p["id"], "code": p.get("default_code") or "", "name": p["name"],
                 "price": p.get("list_price") or 0, "unit": _uom_name(p.get("uom_id"))}
                for p in read("product.product", [["sale_ok", "=", True]], ["name", "default_code", "list_price", "uom_id"])]
    taxes = [{"erp_id": t["id"], "code": str(t.get("amount")), "name": t["name"]}
             for t in read("account.tax", [["type_tax_use", "=", "sale"]], ["name", "amount"])]

    results = {}
    for kind, entries in (("customer", customers), ("product", products), ("tax", taxes)):
        res = push(backend, token, "odoo/18", kind, entries)
        results[kind] = res.get("count")
        extra = ""
        if kind == "product" and res.get("catalog_sync"):
            cs = res["catalog_sync"]
            extra = f" -> catalogo Ordia: +{cs.get('inserted', 0)} nuovi, {cs.get('updated', 0)} aggiornati"
        print(f"[master-data] {kind}: pushed {res.get('count')} entries{extra}")
    return results


def main():
    backend = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ORDIA_BACKEND")
    token = json.load(open(STATE_FILE)).get("token")
    run_sync(backend, token)


if __name__ == "__main__":
    main()
