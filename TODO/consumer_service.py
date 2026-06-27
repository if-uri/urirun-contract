#!/usr/bin/env python3
# Part of the ifURI solution — pakiet KONSUMENTA (proces 2).
"""Serwis HTTP udostępniający ``window/command/restore``. Przyjmuje ``snapshot`` po
transporcie, WALIDUJE wejście wobec inp-schematu wspólnego kontraktu (odrzuca śmieci od
kogokolwiek), wykonuje ciało, waliduje własne wyjście. Ładuje TEN SAM contracts.json co
producent — niezależnie. Łączy ich wyłącznie kontrakt.

  POST /run  {snapshot}  →  koperta window/command/restore
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "toolkit"))
from contract_gate import ContractViolation, check  # noqa: E402
from contracts_io import load  # noqa: E402

ROUTE = "window/command/restore"
CONTRACTS, _ = load()
C = CONTRACTS[ROUTE]


def restore_handler(snapshot: dict) -> dict:
    """CIAŁO handlera. W realu: CDP navigate(url) + rehydrate scroll/forms. Tu: potwierdza
    odtworzenie i zwraca odwracalną kopertę."""
    return {"ok": True, "connector": "windowpair", "action": "window-restore",
            "did": f"restore({snapshot.get('id', '?')})", "reversible": True,
            "inverse": {"path": "window/command/close", "args": {"id": snapshot.get("id")}}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _err(self, code, msg):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": False, "error": msg}).encode())

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
        payload = json.loads(body or b"{}")
        # ENFORCE wejścia: odrzuć payload niezgodny z własnym kontraktem (czyjkolwiek by nie był)
        try:
            check(C.inp, payload, "inp")
        except ContractViolation as exc:
            return self._err(422, f"input violates {ROUTE}: {exc}")
        snap = payload.get("snapshot") or {}
        if not snap.get("url"):
            return self._err(422, "snapshot.url required (remediation: snapshot-url-missing)")
        env = restore_handler(snap)
        try:
            check(C.out, env, "out")
        except ContractViolation as exc:
            return self._err(500, f"output violates {ROUTE}: {exc}")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(env).encode())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8802"))
    print(f"consumer: {ROUTE} na :{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
