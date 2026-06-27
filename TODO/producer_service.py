#!/usr/bin/env python3
# Part of the ifURI solution — pakiet PRODUCENTA (proces 1).
"""Serwis HTTP udostępniający ``window/command/close`` po transporcie (nie potoku).
Buduje kopertę (ciało handlera — to, co człowiek/LLM wypełnia w wygenerowanym stubie),
WALIDUJE ją wobec out-schematu wspólnego kontraktu PRZED wysłaniem (enforce na granicy),
i zwraca JSON. Inny proces — w innym kontenerze, innym języku — czyta tylko ten JSON.

  POST /run  {id?}  →  koperta window/command/close (snapshot + inverse)
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "toolkit"))
from contract_gate import ContractViolation, check  # noqa: E402
from contracts_io import load  # noqa: E402

ROUTE = "window/command/close"
CONTRACTS, _ = load()
C = CONTRACTS[ROUTE]


def close_handler(id: str = "active") -> dict:
    """CIAŁO handlera (wypełnione w wygenerowanym stubie). W realu: CDP snapshot + window.close().
    Tu: deterministyczny snapshot, żeby pokazać przepływ kontraktu między procesami."""
    snapshot = {"url": "https://example.test/x", "scrollX": 0, "scrollY": 240,
                "forms": [], "id": id}
    return {"ok": True, "connector": "windowpair", "action": "window-close",
            "did": f"close({id})", "reversible": True, "snapshot": snapshot,
            "inverse": {"path": "window/command/restore", "args": {"snapshot": snapshot}}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # cisza
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
        payload = json.loads(body or b"{}")
        env = close_handler(id=payload.get("id", "active"))
        # ENFORCE na granicy: nie wypuść koperty niezgodnej z własnym kontraktem
        try:
            check(C.out, env, "out")
        except ContractViolation as exc:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": f"output violates {ROUTE}: {exc}"}).encode())
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(env).encode())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8801"))
    print(f"producer: {ROUTE} na :{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
