#!/usr/bin/env python3
# Part of the ifURI solution — lint pokrycia floty kontraktami.
"""Skanuje katalog z konektorami (`urirun-connector-*`) i raportuje pokrycie kontraktami.
Connector z trasą MUTUJĄCĄ (`/command/`) BEZ kontraktu = naruszenie (z `--strict` → exit 1).

Trasy odkrywane z DWÓCH źródeł: dekoratory `@conn.handler/command/query` w kodzie (źródło
prawdy dla connectorów Python) ORAZ `routes` w `connector.manifest.json`. Connector bez żadnej
wykrywalnej trasy jest raportowany JAWNIE jako „nieznany" — nie cicho przepuszczany (to byłaby
fałszywa zieleń). Kontrakt = `contracts.py`/`contracts.json` poza venv/.git.

  python ci/fleet_coverage.py <root>           # raport (exit 0)
  python ci/fleet_coverage.py <root> --strict  # exit 1 jeśli mutujący bez kontraktu
"""
from __future__ import annotations

import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from urirun_contract.contract_scaffold import discover_routes, effect_of, route_key  # noqa: E402

_SKIP = ("/venv/", "/.git/", "/__pycache__/", "/node_modules/", "/build/", "/dist/")


def _src_files(conn_dir: str, pattern: str) -> list[str]:
    return [p for p in glob.glob(os.path.join(conn_dir, "**", pattern), recursive=True)
            if not any(s in p for s in _SKIP)]


def _has_contract(conn_dir: str) -> bool:
    return any(_src_files(conn_dir, pat) for pat in ("contracts.py", "contracts.json"))


def _routes(conn_dir: str) -> list[str]:
    """Trasy z dekoratorów handlerów (Python) + manifestu, bez duplikatów."""
    found: dict[str, None] = {}
    for py in _src_files(conn_dir, "*.py"):
        try:
            for r in discover_routes(open(py, encoding="utf-8", errors="ignore").read()):
                found.setdefault(r, None)
        except OSError:
            pass
    mani = os.path.join(conn_dir, "connector.manifest.json")
    if os.path.exists(mani):
        try:
            for r in json.load(open(mani)).get("routes", []):
                found.setdefault(route_key(r), None)
        except (OSError, ValueError):
            pass
    return list(found)


def scan(root: str) -> dict:
    conns = sorted(d for d in glob.glob(os.path.join(root, "urirun-connector-*"))
                   if os.path.isdir(d))
    rows = []
    for d in conns:
        has = _has_contract(d)
        routes = _routes(d)
        mut = [r for r in routes if effect_of(r) == "command"]
        rows.append({"name": os.path.basename(d), "has_contract": has,
                     "routes": routes, "mutating": mut,
                     "violation": bool(mut) and not has,
                     "unknown": not routes and not has})
    return {"total": len(rows), "with_contract": sum(r["has_contract"] for r in rows),
            "violations": [r for r in rows if r["violation"]],
            "unknown": [r for r in rows if r["unknown"]], "rows": rows}


def main(argv: list[str]) -> int:
    strict = "--strict" in argv
    args = [a for a in argv if not a.startswith("--")]
    root = args[0] if args else os.path.dirname(ROOT)  # domyślnie monorepo if-uri
    rep = scan(root)

    print(f"Pokrycie floty: {rep['with_contract']}/{rep['total']} konektorów ma kontrakt")
    if rep["violations"]:
        print(f"\nMUTUJĄCE BEZ KONTRAKTU ({len(rep['violations'])}):")
        for r in rep["violations"]:
            print(f"  ✗ {r['name']}  ({len(r['mutating'])} tras command, np. {r['mutating'][0]})")
        print("  → wygeneruj szkielet: `python ci/scaffold_contract.py <connector>`")
    else:
        print("  (brak mutujących bez kontraktu)")
    if rep["unknown"]:
        print(f"\nNIEZNANE ({len(rep['unknown'])}) — brak wykrywalnych tras i kontraktu (nie oceniam):")
        print("  " + ", ".join(r["name"] for r in rep["unknown"]))
    return 1 if (strict and rep["violations"]) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
