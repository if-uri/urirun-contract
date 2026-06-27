#!/usr/bin/env python3
# Part of the ifURI solution — ORCHESTRATOR / brama międzyprocesowa po transporcie.
"""Steruje wymianą między dwoma WDROŻONYMI procesami po HTTP, wiążąc je wspólnym kontraktem:

  1. POST producent  →  koperta window/command/close
  2. zastosuj krawędź WIRES (close→restore: snapshot→snapshot) → zbuduj wejście konsumenta
  3. consumer_input_check → potwierdź PEŁNY handoff (snapshot to całe wejście restore)
  4. POST konsument z tym wejściem  →  koperta window/command/restore
  5. zwaliduj odpowiedź; exit 0/1

Procesy nie współdzielą obiektu Pythona — tylko JSON na sieci i TEN SAM contracts.json.
To jest test, czy dwa NIEZALEŻNIE wdrożone pakiety różnych URI łączą się po transporcie."""
from __future__ import annotations

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "toolkit"))
from contract_gate import check, consumer_input_check, find_wire, wire_payload  # noqa: E402
from contracts_io import load  # noqa: E402

PRODUCER = os.environ.get("PRODUCER_URL", "http://localhost:8801")
CONSUMER = os.environ.get("CONSUMER_URL", "http://localhost:8802")
CONSUMER_GO = os.environ.get("CONSUMER_GO_URL", "")   # opcjonalny; "" = pomiń
CONTRACTS, WIRES = load()


def post(url: str, payload: dict) -> dict:
    req = urllib.request.Request(url + "/run", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def wait_ready(url, tries=40):
    import time
    for _ in range(tries):
        try:
            urllib.request.urlopen(url + "/health", timeout=1); return True
        except Exception:
            time.sleep(0.5)
    raise SystemExit(f"serwis {url} nie wstał")


def _run_pair(label: str, producer_url: str, consumer_url: str) -> int:
    """Jedena runda: producer → wire → consumer po HTTP. Zwraca 0 lub 1."""
    close_env = post(producer_url, {"id": "active"})
    check(CONTRACTS["window/command/close"].out, close_env, "producer.out")

    wire = find_wire(WIRES, "window/command/close", "window/command/restore")
    payload = wire_payload(wire, close_env)
    mode, problems = consumer_input_check(CONTRACTS["window/command/restore"], payload, wire)
    if problems:
        print(f"  ✗ [{label}] krawędź niezgodna ({mode}): {problems}")
        return 1

    restore_env = post(consumer_url, payload)
    check(CONTRACTS["window/command/restore"].out, restore_env, "consumer.out")

    print(f"  [OK ] {label}  ({mode} handoff)")
    print(f"        close.snapshot.url = {close_env['snapshot']['url']}")
    print(f"        restore did        = {restore_env['did']}")
    return 0


def main() -> int:
    wait_ready(PRODUCER)
    wait_ready(CONSUMER)
    code = 0

    # para 1: producer (Python) → consumer (Python)
    code |= _run_pair("producer(py) ──HTTP──▶ consumer(py)", PRODUCER, CONSUMER)

    # para 2 (opcjonalna): producer (Python) → consumer (Go) — polyglot end-to-end
    if CONSUMER_GO:
        wait_ready(CONSUMER_GO)
        code |= _run_pair("producer(py) ──HTTP──▶ consumer(go)", PRODUCER, CONSUMER_GO)

    if code == 0:
        print("  wszystkie pary OK — dwa wdrożone pakiety różnych URI i języków, jeden kontrakt")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
