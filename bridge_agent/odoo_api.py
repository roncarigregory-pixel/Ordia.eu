#!/usr/bin/env python3
"""Ordia Bridge — direct ERP API delivery (Class A / cloud ERP with API).

Creates the order via Odoo's JSON-RPC API (fastest, most robust channel — no UI).
Exposed as deliver_via_api() for the Bridge agent; also runnable standalone.
Comparison baseline for the RPA channel.
"""
import asyncio
import json
import os
import sys
import urllib.request


def _rpc(url, service, method, args):
    payload = {"jsonrpc": "2.0", "method": "call",
               "params": {"service": service, "method": method, "args": args}}
    req = urllib.request.Request(url + "/jsonrpc", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "OrdiaBridge/1.0"})
    return json.load(urllib.request.urlopen(req, timeout=45)).get("result")


def _map(v, mapping, default):
    return (mapping or {}).get(v, default or v)


async def deliver_via_api(std_order: dict, cfg: dict) -> dict:
    url = cfg.get("odoo_url", "http://localhost:8069")
    db = cfg.get("db", "ordia")
    login = cfg.get("login", "admin")
    password = cfg.get("password", "admin")

    uid = _rpc(url, "common", "authenticate", [db, login, password, {}])
    if not uid:
        raise RuntimeError("Odoo API authentication failed")

    def call(model, method, args, kwargs=None):
        return _rpc(url, "object", "execute_kw", [db, uid, password, model, method, args, kwargs or {}])

    cust_name = _map((std_order.get("customer") or {}).get("name"),
                     cfg.get("customer_map"), cfg.get("default_customer", "Azure Interior"))
    pids = call("res.partner", "search", [[["name", "=", cust_name]]], {"limit": 1})
    if not pids:
        raise RuntimeError(f"Customer '{cust_name}' not found in ERP")
    partner_id = pids[0]

    order_lines = []
    mapped = []
    for l in std_order.get("lines", []):
        pname = _map(l.get("product"), cfg.get("product_map"), cfg.get("default_product", "Storage Box"))
        prod = call("product.product", "search", [[["name", "=", pname]]], {"limit": 1})
        if not prod:
            prod = call("product.product", "search", [[["name", "ilike", pname]]], {"limit": 1})
        if not prod:
            raise RuntimeError(f"Product '{pname}' not found in ERP")
        qty = l.get("quantity") or 1
        order_lines.append((0, 0, {"product_id": prod[0], "product_uom_qty": qty}))
        mapped.append((l.get("product"), pname, qty))

    order_id = call("sale.order", "create", [{"partner_id": partner_id, "order_line": order_lines}])
    rec = call("sale.order", "read", [[order_id]], {"fields": ["name", "amount_total"]})[0]
    return {"order_ref": rec["name"], "customer": cust_name, "lines": len(order_lines),
            "total": rec["amount_total"], "engine": "odoo-json-rpc", "mapped": mapped}


async def _main():
    order = {"customer": {"name": "Azure Interior"},
             "lines": [{"product": "Large Cabinet", "quantity": 3}]}
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        with open(sys.argv[1]) as f:
            order = json.load(f)
    cfg = {"odoo_url": os.environ.get("ODOO_URL", "http://localhost:8069"), "db": "ordia",
           "login": "admin", "password": "admin"}
    print(f"[RESULT] {await deliver_via_api(order, cfg)}")


if __name__ == "__main__":
    asyncio.run(_main())
