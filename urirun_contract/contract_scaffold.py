# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Szkielet kontraktu z manifestu connectora — adopcja floty GENERACJĄ, nie ręką.

`connector.manifest.json` już deklaruje `routes` (URI z czasownikiem) i `examples` (payloady).
Z tego wyprowadzamy szkielet `contracts.json`: trasa, efekt (z czasownika query/command),
wejście (wywnioskowane z przykładów), przykłady. Człowiek/LLM uzupełnia `out`, `reversible`
i `errors`; `conform` egzekwuje. Bez tego adopcja na ~37 konektorów = dryf ×37.

Wynik jest CELOWO niekompletny (puste `out`) — to punkt zaczepienia do edycji deklaracji,
nie gotowy kontrakt. `scaffold_gaps()` mówi, czego brakuje.
"""
from __future__ import annotations

import re
from typing import Any

_VERBS = ("query", "command")

# @conn.handler("route") / @conn.command("route") / @conn.query("route")
_HANDLER_RE = re.compile(r"\.(?:handler|command|query)\(\s*['\"]([^'\"]+)['\"]")


def discover_routes(py_source: str) -> list[str]:
    """Trasy z dekoratorów ``@conn.handler/command/query`` w kodzie Python (kolejność, bez duplikatów)."""
    seen: dict[str, None] = {}
    for m in _HANDLER_RE.finditer(py_source):
        seen.setdefault(m.group(1), None)
    return list(seen)


def _token_of(value: Any) -> str:
    """Token mini-schematu wywnioskowany z wartości przykładu."""
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "num"
    if isinstance(value, str):
        return "str"
    if isinstance(value, dict):
        return "obj"
    if isinstance(value, list):
        return "list"
    return "any"


def route_key(uri: str) -> str:
    """``scheme://host/noun/verb/action`` → ``noun/verb/action``; bez ``://`` zwraca bez zmian
    (trasa z dekoratora handlera jest już kluczem)."""
    if "://" not in uri:
        return uri
    after = uri.split("://", 1)[-1]
    segs = after.split("/")
    return "/".join(segs[1:]) if len(segs) > 1 else after


def effect_of(route: str) -> str:
    """Efekt z czasownika w trasie: ``command`` jeśli obecny, inaczej ``query``."""
    segs = route.split("/")
    if "command" in segs:
        return "command"
    return "query"


def effect_inferable(route: str) -> bool:
    """Czy efekt DA SIĘ wywnioskować z czasownika URI (`/command/` lub `/query/` w ścieżce). False =
    URI łamie konwencję noun/verb/action (np. ksef `auth/challenge`, `cert/enroll` — czasownik na
    końcu), więc `effect_of` ZGADUJE `query`, a `conform` (efekt↔czasownik) to odrzuci. `scaffold_gaps`
    nagłaśnia to zamiast cicho przepuszczać zły domysł."""
    segs = route.split("/")
    return "command" in segs or "query" in segs


def _infer_inp(examples: list[dict]) -> dict:
    """Pola wejścia z przykładów: wymagane jeśli w KAŻDYM, opcjonalne jeśli w niektórych."""
    payloads = [ex.get("payload", {}) for ex in examples if isinstance(ex.get("payload"), dict)]
    if not payloads:
        return {}
    all_keys: dict[str, str] = {}
    for p in payloads:
        for k, v in p.items():
            all_keys.setdefault(k, _token_of(v))
    inp = {}
    for k, tok in all_keys.items():
        present_everywhere = all(k in p for p in payloads)
        inp[k] = tok if present_everywhere else f"?{tok}"
    return inp


def contracts_from_routes(routes: list[str],
                          examples_by_route: "dict[str, list[dict]] | None" = None) -> dict:
    """Lista tras (z manifestu albo dekoratorów) → szkielet neutralnego `contracts.json`."""
    examples_by_route = examples_by_route or {}
    contracts: dict[str, dict] = {}
    for uri in routes:
        rk = route_key(uri)
        exs = examples_by_route.get(rk, [])
        contracts[rk] = {
            "version": "v1",
            "effect": effect_of(rk),
            "reversible": False,
            "inp": _infer_inp(exs),
            "out": {},  # TODO: uzupełnić kształt wyjścia (conform tego pilnuje)
            "errors": [],
            "examples": [{"payload": ex.get("payload", {})} for ex in exs],
        }
    return {"contracts": contracts, "wires": []}


def contracts_from_manifest(manifest: dict) -> dict:
    """Manifest connectora → szkielet neutralnego `contracts.json` (do uzupełnienia)."""
    by_route: dict[str, list[dict]] = {}
    for ex in manifest.get("examples", []):
        uri = ex.get("uri")
        if uri:
            by_route.setdefault(route_key(uri), []).append(ex)
    return contracts_from_routes(manifest.get("routes", []), by_route)


def routes_from_bindings(bindings: dict) -> list[str]:
    """Trasy z runtime'owego `urirun_bindings()` connectora. Dla connectorów, które budują bindings
    PROGRAMOWO / deklaratywnie przez entry-point ``urirun.bindings`` (a nie dekoratorami
    ``@conn.handler``, których szuka ``discover_routes``). Np. ``urirun-connector-ksef``: 0
    dekoratorów, ale ``urirun_bindings()`` zwraca ~39 tras ``ksef://…`` — bez tego są „nieznane"."""
    routes = bindings.get("bindings", bindings) if isinstance(bindings, dict) else bindings
    return list(routes) if isinstance(routes, dict) else list(routes or [])


def contracts_from_bindings(bindings: dict) -> dict:
    """Runtime `urirun_bindings()` → szkielet neutralnego `contracts.json` (do uzupełnienia).
    Most dla connectorów entry-point/deklaratywnych, których ``discover_routes`` (dekoratory) nie
    widzi; przykłady z koperty bindingu trafiają do `inp`, reszta zostaje pusta (`scaffold_gaps`)."""
    routes = bindings.get("bindings", bindings) if isinstance(bindings, dict) else bindings
    by_route: dict[str, list[dict]] = {}
    if isinstance(routes, dict):
        for uri, spec in routes.items():
            exs = spec.get("examples", []) if isinstance(spec, dict) else []
            for ex in exs:
                if isinstance(ex, dict):
                    by_route.setdefault(route_key(uri), []).append(ex)
    return contracts_from_routes(routes_from_bindings(bindings), by_route)


def scaffold_gaps(contracts_doc: dict) -> list[str]:
    """Czego brakuje w szkielecie, żeby kontrakt był pełny (out, reversible-inverse, przykłady-result)."""
    gaps: list[str] = []
    for route, c in contracts_doc.get("contracts", {}).items():
        if not effect_inferable(route):
            gaps.append(f"{route}: efekt NIE wywnioskowany z URI (brak `/command/`//`/query/`) — "
                        f"szkielet zgadł `{c.get('effect')}`; zadeklaruj efekt ręcznie "
                        f"(conform odrzuci, dopóki URI łamie noun/verb/action)")
        if not c.get("out"):
            gaps.append(f"{route}: pusty `out` — uzupełnij kształt wyjścia")
        if c.get("effect") == "command" and not c.get("reversible"):
            gaps.append(f"{route}: command bez `reversible` — ustal odwracalność (+ inverseRoute)")
        for i, ex in enumerate(c.get("examples", [])):
            if "result" not in ex:
                gaps.append(f"{route}: examples[{i}] bez `result` — dodaj złotą kopertę")
    return gaps
