#!/usr/bin/env python3
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Generic Python gate — reads any neutral contracts.json; reuses urirun_contract kernel.

The 'serve' mode uses golden ok examples from the contracts as the fake handler response,
so this peer works as a conformance node for ANY connector's contracts.json.

  produce <route>        — emit the first golden ok envelope as JSON
  consume <prod> <cons>  — read JSON from stdin, build consumer input, validate
  conform                — run conformance assertions on the loaded contracts.json
  serve [--lie]          — JSON-lines RPC server: {route,payload} → golden envelope
  serve-http [--lie]     — same handler behind HTTP POST /; prints "READY <port>"
"""
from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
# Generyczny węzeł: CONTRACTS wskazuje na contracts.json DOWOLNEGO connectora.
# Domyślnie kanoniczny egzemplarz windowpair (katalog xlang/ nie trzyma kopii).
_CONTRACTS_PATH = os.environ.get(
    "CONTRACTS",
    os.path.join(HERE, "..", "examples", "windowpair", "contracts.json"),
)
_DOC = json.load(open(_CONTRACTS_PATH))
CONTRACTS = {route: SimpleNamespace(**{**c, "inverse_route": c.get("inverseRoute") or ""})
             for route, c in _DOC["contracts"].items()}
WIRES = [SimpleNamespace(**w) for w in _DOC.get("wires", [])]

sys.path.insert(0, os.path.join(HERE, ".."))  # uruchamialny jako skrypt bez instalacji
from urirun_contract import consumer_input_check, wire_payload  # noqa: E402
from urirun_contract.gate import check, conform as _conform     # noqa: E402


def _find_wire(producer: str, consumer: str):
    for w in WIRES:
        if w.producer == producer and w.consumer == consumer:
            return w
    raise KeyError(f"brak krawędzi {producer} -> {consumer}")


def _ok_example(route: str) -> dict:
    for ex in CONTRACTS[route].examples:
        if ex["result"].get("ok"):
            return ex["result"]
    raise SystemExit(f"{route}: brak złotej koperty ok")


def handle(route: str, payload: dict, lie: bool = False) -> dict:
    """Return the first golden ok example for the route (generic, no connector logic)."""
    env = dict(_ok_example(route))
    if lie:
        # corrupt one numeric field → string to model serialization lie for --lie tests
        for k, v in env.items():
            if isinstance(v, int) and k != "ok":
                env[k] = str(v)
                break
    return env


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "conform"
    if cmd == "conform":
        failures = 0
        ns_contracts = {}
        for route, c in _DOC["contracts"].items():
            from urirun_contract import Contract
            ns_contracts[route] = Contract(
                version=c.get("version", "v1"),
                effect=c.get("effect", "query"),
                reversible=c.get("reversible", False),
                inverse_route=c.get("inverseRoute", ""),
                inp=c.get("inp", {}),
                out=c.get("out", {}),
                errors=tuple(c.get("errors", [])),
                examples=tuple(c.get("examples", [])),
            )
        try:
            _conform(ns_contracts)
            print(f"  OK: {len(ns_contracts)} kontraktów konformuje (walidator Python, wspólny contracts.json)")
        except AssertionError as e:
            print(f"  FAIL {e}")
            failures += 1
        return failures
    if cmd == "produce":
        json.dump(_ok_example(sys.argv[2]), sys.stdout)
        return 0
    if cmd == "consume":
        producer, consumer = sys.argv[2], sys.argv[3]
        envelope = json.load(sys.stdin)
        wire = _find_wire(producer, consumer)
        payload = wire_payload(wire, envelope)
        mode, problems = consumer_input_check(CONTRACTS[consumer], payload, wire)
        json.dump({"ok": not problems, "mode": mode, "builtInput": payload, "problems": problems},
                  sys.stdout)
        return 0 if not problems else 1
    if cmd == "serve":
        lie = "--lie" in sys.argv[2:]
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            req = json.loads(line)
            env = handle(req["route"], req.get("payload") or {}, lie)
            sys.stdout.write(json.dumps({"id": req.get("id"), "envelope": env}) + "\n")
            sys.stdout.flush()
        return 0
    if cmd == "serve-http":
        from http.server import BaseHTTPRequestHandler, HTTPServer
        lie = "--lie" in sys.argv[2:]

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(n) or b"{}")
                env = handle(req["route"], req.get("payload") or {}, lie)
                body = json.dumps({"id": req.get("id"), "envelope": env}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        srv = HTTPServer(("127.0.0.1", 0), H)
        print(f"READY {srv.server_address[1]}", flush=True)
        srv.serve_forever()
        return 0
    raise SystemExit(f"nieznany tryb {cmd!r}")


if __name__ == "__main__":
    raise SystemExit(main())
