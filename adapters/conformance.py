#!/usr/bin/env python3
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Zewnętrzny driver konformancji — bije w ŻYWY węzeł po transporcie i sprawdza,
czy jego odpowiedź na drucie jest zgodna z kontraktem.

`conform` (gate.py) waliduje kontrakt i złoty korpus *u siebie* — w jednym procesie.
Węzeł może mieć kontrakt, który konformuje lokalnie, a mimo to **kłamać na drucie**:
zserializować int jako string, zgubić pole, zwrócić nieobjętą taksonomią klasę błędu.
Ten driver to łapie, bo czyta to, co realnie wyszło z gniazda HTTP — nie obiekt Pythona.

Dla każdej trasy ze złotym przykładem ok:
  1. weź `payload` ze złotego przykładu jako wejście,
  2. POST do węzła po wybranym profilu transportu,
  3. wyciągnij kopertę z odpowiedzi,
  4. `envelope_violation(contract, envelope)` → komunikat naruszenia albo None.

Profile transportu (jak zbudować żądanie i skąd wziąć kopertę):
  peer    — generyczny węzeł `xlang/peer.py serve-http`: POST `/`,
            ciało `{route, payload}`, koperta = odpowiedź["envelope"]. Steruje WSZYSTKIE trasy.
  direct  — usługa zbudowana pod jedną trasę (np. Go `consumer-go`): POST `<endpoint>`,
            ciało = sam payload, koperta = całe ciało odpowiedzi.

Exit code = liczba tras, które naruszyły kontrakt na drucie (0 = węzeł zgodny).

Użycie:
  conformance.py --node http://127.0.0.1:8811                 # profil peer, wszystkie trasy
  conformance.py --node http://127.0.0.1:8803 --profile direct \
                 --route window/command/restore --endpoint /run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from urirun_contract import Contract, envelope_violation  # noqa: E402

_DEFAULT_CONTRACTS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples", "windowpair", "contracts.json",
)


def load_contracts(path: str) -> dict[str, Contract]:
    """Wczytaj neutralny contracts.json do obiektów Contract (klucz = trasa)."""
    doc = json.load(open(path))
    out: dict[str, Contract] = {}
    for route, c in doc["contracts"].items():
        out[route] = Contract(
            version=c.get("version", "v1"),
            effect=c.get("effect", "query"),
            reversible=c.get("reversible", False),
            inverse_route=c.get("inverseRoute", ""),
            inp=c.get("inp", {}),
            out=c.get("out", {}),
            errors=tuple(c.get("errors", [])),
            examples=tuple(c.get("examples", [])),
        )
    return out


def golden_payload(contract: Contract) -> "dict | None":
    """Payload pierwszego złotego przykładu ok, albo None gdy brak."""
    for ex in contract.examples:
        if ex.get("result", {}).get("ok"):
            return ex.get("payload", {})
    return None


def _post(url: str, body: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def wait_ready(base: str, tries: int = 40, delay: float = 0.25) -> None:
    """Czekaj aż /health odpowie; bez /health — aż POST przestanie rzucać ConnectionError."""
    for _ in range(tries):
        try:
            urllib.request.urlopen(base + "/health", timeout=1)
            return
        except urllib.error.HTTPError:
            return  # serwis żyje, po prostu nie ma /health
        except Exception:
            time.sleep(delay)
    raise SystemExit(f"węzeł {base} nie wstał")


def call_node(base: str, route: str, payload: dict, *, profile: str,
              endpoint: str, timeout: float) -> dict:
    """Wyślij wejście trasy do węzła wg profilu i zwróć KOPERTĘ z drutu."""
    if profile == "peer":
        resp = _post(base.rstrip("/") + "/", {"route": route, "payload": payload}, timeout)
        return resp.get("envelope", resp)
    if profile == "direct":
        return _post(base.rstrip("/") + endpoint, payload, timeout)
    raise SystemExit(f"nieznany profil {profile!r}")


def drive(base: str, contracts: dict[str, Contract], *, profile: str, endpoint: str,
          routes: "list[str] | None", timeout: float) -> int:
    """Steruj każdą trasą i zwaliduj kopertę z drutu. Zwraca liczbę naruszeń."""
    selected = routes or list(contracts)
    violations = 0
    checked = 0
    for route in selected:
        contract = contracts.get(route)
        if contract is None:
            print(f"  ✗ {route}: brak takiego kontraktu w contracts.json")
            violations += 1
            continue
        payload = golden_payload(contract)
        if payload is None:
            print(f"  ·  {route}: brak złotej koperty ok — pomijam")
            continue
        try:
            envelope = call_node(base, route, payload, profile=profile,
                                 endpoint=endpoint, timeout=timeout)
        except Exception as exc:
            print(f"  ✗ {route}: transport padł: {exc}")
            violations += 1
            continue
        checked += 1
        problem = envelope_violation(contract, envelope)
        if problem:
            print(f"  ✗ {route}: KŁAMSTWO NA DRUCIE — {problem}")
            violations += 1
        else:
            print(f"  [OK ] {route}: koperta z drutu zgodna z kontraktem")
    print(f"  → {checked} tras sprawdzonych, {violations} naruszeń")
    return violations


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="Zewnętrzny driver konformancji żywego węzła")
    ap.add_argument("--node", required=True, help="bazowy URL żywego węzła")
    ap.add_argument("--contracts", default=os.environ.get("CONTRACTS", _DEFAULT_CONTRACTS),
                    help="ścieżka do neutralnego contracts.json")
    ap.add_argument("--profile", default="peer", choices=("peer", "direct"),
                    help="profil transportu (domyślnie peer)")
    ap.add_argument("--endpoint", default="/run",
                    help="ścieżka POST dla profilu direct (domyślnie /run)")
    ap.add_argument("--route", action="append", dest="routes",
                    help="ogranicz do tej trasy (można podać wielokrotnie)")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--no-wait", action="store_true", help="nie czekaj na gotowość węzła")
    args = ap.parse_args(argv)

    contracts = load_contracts(args.contracts)
    if not args.no_wait:
        wait_ready(args.node)
    print(f"driver → {args.node} (profil {args.profile}, kontrakt {os.path.basename(args.contracts)})")
    return drive(args.node, contracts, profile=args.profile, endpoint=args.endpoint,
                 routes=args.routes, timeout=args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
