#!/usr/bin/env python3
# Part of the ifURI solution — lint pokrycia floty kontraktami.
"""Skanuje katalog z konektorami (`urirun-connector-*`) i raportuje pokrycie kontraktami.
Connector z trasą MUTUJĄCĄ (`/command/`) BEZ kontraktu = naruszenie (z `--strict` → exit 1).

Trasy odkrywane z TRZECH źródeł: dekoratory `@conn.handler/command/query` w kodzie (źródło prawdy
dla connectorów Python), `routes` w `connector.manifest.json`, ORAZ — gdy oba zawiodą — runtime
`urirun_bindings()` przez entry-point `urirun.bindings` (connectory budujące bindings PROGRAMOWO,
np. ksef: 0 dekoratorów, ~39 tras). Connector bez ŻADNEJ wykrywalnej trasy (np. biblioteka bez
powierzchni URI, jak scanner) jest raportowany JAWNIE jako „nieznany" — nie cicho przepuszczany (to
byłaby fałszywa zieleń); świadome wyjątki idą do `known_unknown` w baseline. Kontrakt =
`contracts.py`/`contracts.json` poza venv/.git.

  python ci/fleet_coverage.py <root>                         # raport (exit 0)
  python ci/fleet_coverage.py <root> --strict                # exit 1 jeśli mutujący bez kontraktu
  python ci/fleet_coverage.py <root> --baseline known.json   # exit 1 tylko na nowe braki/unknown
"""
from __future__ import annotations

import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from urirun_contract.contract_scaffold import (  # noqa: E402
    discover_routes, effect_of, route_key, routes_from_bindings,
)

_SKIP = ("/venv/", "/.git/", "/__pycache__/", "/node_modules/", "/build/", "/dist/")


def _entry_point_targets(conn_dir: str, group: str) -> list[str]:
    """Cele entry-pointów z grupy (np. `urirun.bindings`) z pyproject.toml — STATYCZNIE, bez importu.
    Pozwala odróżnić connector z bindings (ksef) od serwisu (`urirun.services`, np. scanner)."""
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - py<3.11
        return []
    out: list[str] = []
    for pp in _src_files(conn_dir, "pyproject.toml"):
        try:
            data = tomllib.load(open(pp, "rb"))
        except (OSError, ValueError):
            continue
        eps = data.get("project", {}).get("entry-points", {}).get(group, {})
        out.extend(str(v) for v in eps.values())
    return out


def _bindings_routes(conn_dir: str) -> list[str]:
    """Trzecie źródło tras: runtime `urirun_bindings()` przez entry-point `urirun.bindings`. Dla
    connectorów budujących bindings PROGRAMOWO/deklaratywnie (np. ksef: 0 dekoratorów, ~39 tras),
    których `discover_routes` (dekoratory) nie widzi. Import jest STRZEŻONY — lint nie wywala się na
    connectorze, którego zależności nie są zainstalowane (zwraca [] i trasa zostaje „nieznana")."""
    import importlib
    found: list[str] = []
    for target in _entry_point_targets(conn_dir, "urirun.bindings"):
        mod_name, _, func = target.partition(":")
        try:
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, func or "urirun_bindings", None)
            if callable(fn):
                found.extend(route_key(r) for r in routes_from_bindings(fn()))
        except Exception:  # noqa: BLE001 - a lint tool must not crash on an unimportable connector
            continue
    return found


def _src_files(conn_dir: str, pattern: str) -> list[str]:
    return [p for p in glob.glob(os.path.join(conn_dir, "**", pattern), recursive=True)
            if not any(s in p for s in _SKIP)]


def _has_contract(conn_dir: str) -> bool:
    return any(_src_files(conn_dir, pat) for pat in ("contracts.py", "contracts.json"))


def _contract_keys(conn_dir: str) -> set[str]:
    """Trasy, które kontrakt connectora REALNIE deklaruje (klucze CONTRACTS / contracts.json).
    Niektóre connectory są keyed pełnym URI (browser-control/webnode), inne route_key — bierzemy jak są;
    dopasowanie normalizuje obie strony (`_norm`). Import contracts.py jest STRZEŻONY."""
    keys: set[str] = set()
    for cj in _src_files(conn_dir, "contracts.json"):
        try:
            keys |= set(json.load(open(cj)).get("contracts", {}))
        except (OSError, ValueError):
            pass
    if _src_files(conn_dir, "contracts.py"):
        pkg = os.path.basename(conn_dir).replace("urirun-connector-", "urirun_connector_").replace("-", "_")
        try:
            import importlib
            keys |= set(getattr(importlib.import_module(f"{pkg}.contracts"), "CONTRACTS", {}) or {})
        except Exception:  # noqa: BLE001 - lint nie wywala się na nieimportowalnym connectorze
            pass
    return keys


def _norm(route: str) -> set[str]:
    """Formy porównawcze trasy odporne na schemat kluczowania (pełny URI vs route_key): sama trasa,
    `route_key`, oraz ostatnie 2 segmenty (verb/action) — żeby dopasować mimo różnic w prefiksie."""
    forms = {route, route_key(route)}
    for r in (route, route_key(route)):
        parts = [p for p in r.split("/") if p]
        if len(parts) >= 2:
            forms.add("/".join(parts[-2:]))
    return forms


def _uncovered_mutating(mutating: list[str], contract_keys: set[str]) -> list[str]:
    """Trasy MUTUJĄCE bez odpowiadającego wpisu w kontrakcie (dopasowanie permisywne — flaguje tylko
    gdy ŻADNA forma trasy nie pasuje do ŻADNEJ formy klucza kontraktu, by uniknąć fałszywych braków)."""
    contract_forms: set[str] = set()
    for k in contract_keys:
        contract_forms |= _norm(k)
    return [r for r in mutating if not (_norm(r) & contract_forms)]


def _routes(conn_dir: str) -> list[str]:
    """Trasy z dekoratorów handlerów (Python) + manifestu, bez duplikatów."""
    found: dict[str, None] = {}
    for py in _src_files(conn_dir, "*.py"):
        try:
            for r in discover_routes(open(py, encoding="utf-8", errors="ignore").read()):
                found.setdefault(r, None)
        except OSError:
            pass
    for mani in _src_files(conn_dir, "connector.manifest.json"):
        try:
            for r in json.load(open(mani)).get("routes", []):
                found.setdefault(route_key(r), None)
        except (OSError, ValueError):
            pass
    # Trzecie źródło — TYLKO gdy statyczne nic nie dało (efektywność: importujemy connector tylko
    # gdy inaczej byłby „nieznany"). Łapie ksef-klasę (programmatic `urirun_bindings()`).
    if not found:
        for r in _bindings_routes(conn_dir):
            found.setdefault(r, None)
    return list(found)


def scan(root: str) -> dict:
    conns = sorted(d for d in glob.glob(os.path.join(root, "urirun-connector-*"))
                   if os.path.isdir(d))
    rows = []
    for d in conns:
        has = _has_contract(d)
        routes = _routes(d)
        mut = [r for r in routes if effect_of(r) == "command"]
        # Route-level: connector MA kontrakt, ale część tras mutujących nie ma wpisu (np. twin 3/23).
        uncov = _uncovered_mutating(mut, _contract_keys(d)) if has and mut else []
        rows.append({"name": os.path.basename(d), "has_contract": has,
                     "routes": routes, "mutating": mut, "uncovered_mutating": uncov,
                     "violation": bool(mut) and not has,
                     "partial": has and bool(uncov),
                     "unknown": not routes and not has})
    return {"total": len(rows), "with_contract": sum(r["has_contract"] for r in rows),
            "violations": [r for r in rows if r["violation"]],
            "partial": [r for r in rows if r["partial"]],
            "unknown": [r for r in rows if r["unknown"]], "rows": rows}


def _arg_value(argv: list[str], name: str) -> str | None:
    for i, item in enumerate(argv):
        if item == name and i + 1 < len(argv):
            return argv[i + 1]
        if item.startswith(name + "="):
            return item.split("=", 1)[1]
    return None


def _baseline_doc(path: str | None) -> dict:
    if not path or not os.path.exists(path):
        return {}
    doc = json.load(open(path))
    if isinstance(doc, list):
        return {"known_violations": doc}
    return doc if isinstance(doc, dict) else {}


def _baseline_names(doc_or_path: dict | str | None) -> set[str]:
    doc = _baseline_doc(doc_or_path) if not isinstance(doc_or_path, dict) else doc_or_path
    raw = doc.get("known_violations", doc if isinstance(doc, list) else [])
    return {str(item) for item in raw}


def _baseline_unknown_names(doc_or_path: dict | str | None) -> set[str]:
    doc = _baseline_doc(doc_or_path) if not isinstance(doc_or_path, dict) else doc_or_path
    return {str(item) for item in doc.get("known_unknown", [])}


def _baseline_partial_names(doc_or_path: dict | str | None) -> set[str]:
    doc = _baseline_doc(doc_or_path) if not isinstance(doc_or_path, dict) else doc_or_path
    return {str(item) for item in doc.get("known_partial", [])}


def new_violations(rep: dict, known: set[str]) -> list[dict]:
    return [r for r in rep["violations"] if r["name"] not in known]


def new_unknown(rep: dict, known: set[str]) -> list[dict]:
    return [r for r in rep["unknown"] if r["name"] not in known]


def new_partial(rep: dict, known: set[str]) -> list[dict]:
    return [r for r in rep["partial"] if r["name"] not in known]


def main(argv: list[str]) -> int:
    strict = "--strict" in argv
    baseline_path = _arg_value(argv, "--baseline")
    args = [a for a in argv
            if not a.startswith("--") and a != (baseline_path or "")]
    root = args[0] if args else os.path.dirname(ROOT)  # domyślnie monorepo if-uri
    rep = scan(root)
    baseline = _baseline_doc(baseline_path)
    known = _baseline_names(baseline)
    known_unknown = _baseline_unknown_names(baseline)
    known_partial = _baseline_partial_names(baseline)
    new = new_violations(rep, known)
    unknown_new = new_unknown(rep, known_unknown)
    unknown_known = [r for r in rep["unknown"] if r["name"] in known_unknown]
    partial_new = new_partial(rep, known_partial)

    print(f"Pokrycie floty: {rep['with_contract']}/{rep['total']} konektorów ma kontrakt")
    if rep["violations"]:
        print(f"\nMUTUJĄCE BEZ KONTRAKTU ({len(rep['violations'])}):")
        for r in rep["violations"]:
            print(f"  ✗ {r['name']}  ({len(r['mutating'])} tras command, np. {r['mutating'][0]})")
        print("  → wygeneruj szkielet: `python ci/scaffold_contract.py <connector>`")
    else:
        print("  (brak mutujących bez kontraktu)")
    if rep["partial"]:
        print(f"\nCZĘŚCIOWE POKRYCIE ({len(rep['partial'])}) — connector MA kontrakt, ale część tras "
              f"mutujących nie ma wpisu (route-level):")
        for r in rep["partial"]:
            print(f"  ~ {r['name']}  ({len(r['uncovered_mutating'])}/{len(r['mutating'])} mutujących "
                  f"bez kontraktu, np. {r['uncovered_mutating'][0]})")
    if baseline_path:
        print(f"\nBaseline: {len(known)} znanych braków, {len(known_partial)} znanych częściowych, "
              f"{len(known_unknown)} znanych unknown ({baseline_path})")
        if partial_new:
            print(f"NOWE CZĘŚCIOWE ({len(partial_new)}):")
            for r in partial_new:
                print(f"  ~ {r['name']}")
        else:
            print("  brak nowych częściowych względem baseline")
        if new:
            print(f"NOWE BRAKI ({len(new)}):")
            for r in new:
                print(f"  ✗ {r['name']}")
        else:
            print("  brak nowych braków względem baseline")
        if unknown_new:
            print(f"NOWE NIEZNANE ({len(unknown_new)}):")
            for r in unknown_new:
                print(f"  ? {r['name']}")
        else:
            print("  brak nowych unknown względem baseline")
    if unknown_new:
        print(f"\nNIEZNANE ({len(unknown_new)}) — brak wykrywalnych tras i kontraktu (nie oceniam):")
        print("  " + ", ".join(r["name"] for r in unknown_new))
    if unknown_known:
        print(f"\nZNANE BEZ POWIERZCHNI URI ({len(unknown_known)}) — świadomie poza fleet coverage:")
        print("  " + ", ".join(r["name"] for r in unknown_known))
    if strict and (rep["violations"] or rep["partial"]):
        return 1
    if baseline_path and (new or unknown_new or partial_new):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
