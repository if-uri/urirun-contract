#!/usr/bin/env python3
# Part of the ifURI solution — szkielet contracts.json z manifestu connectora (adopcja floty).
"""Emituje szkielet contracts.json z connectora: trasy z dekoratorów `@conn.handler` (kod) i/lub
`connector.manifest.json`, efekt z czasownika, wejście z przykładów. Człowiek/LLM uzupełnia
`out`/`reversible`/`errors`; `conform` egzekwuje.

Importuje generator z urirun_contract (jedyne źródło — nie przepisuj tu reguł).

  python ci/scaffold_contract.py <connector-dir>          # skan core.py + manifest → stdout
  python ci/scaffold_contract.py <manifest.json>          # tylko manifest
  python ci/scaffold_contract.py <źródło> contracts.json  # zapis do pliku

Wymaga: pip install urirun-contract
"""
from __future__ import annotations

import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from urirun_contract.contract_scaffold import (  # noqa: E402
    contracts_from_manifest, contracts_from_routes, discover_routes, route_key, scaffold_gaps,
)

_SKIP = ("/venv/", "/.git/", "/__pycache__/", "/node_modules/")


def _doc_from_dir(conn_dir: str) -> dict:
    """Trasy z dekoratorów handlerów (wszystkie *.py) + manifestu."""
    routes: dict[str, None] = {}
    examples_by_route: dict[str, list] = {}
    for py in glob.glob(os.path.join(conn_dir, "**", "*.py"), recursive=True):
        if any(s in py for s in _SKIP):
            continue
        try:
            for r in discover_routes(open(py, encoding="utf-8", errors="ignore").read()):
                routes.setdefault(r, None)
        except OSError:
            pass
    mani = os.path.join(conn_dir, "connector.manifest.json")
    if os.path.exists(mani):
        m = json.load(open(mani))
        for r in m.get("routes", []):
            routes.setdefault(route_key(r), None)
        for ex in m.get("examples", []):
            if ex.get("uri"):
                examples_by_route.setdefault(route_key(ex["uri"]), []).append(ex)
    return contracts_from_routes(list(routes), examples_by_route)


def main(argv: list[str]) -> int:
    if not argv:
        print("użycie: scaffold_contract.py <connector-dir | manifest.json> [out.json]", file=sys.stderr)
        return 2
    src = argv[0]
    if os.path.isdir(src):
        doc = _doc_from_dir(src)
    elif src.endswith(".json"):
        doc = contracts_from_manifest(json.load(open(src)))
    else:
        print(f"nie wiem jak czytać {src!r} (podaj katalog connectora albo manifest.json)", file=sys.stderr)
        return 2
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"

    out = argv[1] if len(argv) > 1 else "-"
    if out == "-":
        sys.stdout.write(text)
    else:
        open(out, "w").write(text)
        print(f"napisano {out} ({len(doc['contracts'])} tras)", file=sys.stderr)

    gaps = scaffold_gaps(doc)
    if gaps:
        print(f"\nDO UZUPEŁNIENIA ({len(gaps)}):", file=sys.stderr)
        for g in gaps:
            print(f"  · {g}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
