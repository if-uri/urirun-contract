#!/usr/bin/env python3
# Part of the ifURI solution — generator deterministyczny (kontrakt → kod).
"""Czyta contracts.json i emituje src/handlers_generated.py: sygnatury + kształt koperty
z kontraktu. To jest artefakt GENEROWANY i commitowany — regen_check pilnuje, że nikt go
ręcznie nie zedytował ani nie zapomniał przegenerować po zmianie kontraktu.

W realnym template: ``from urirun_connectors_toolkit.contract_codegen import py_stub``.
Tu importujemy lokalny codegen i podajemy mu kontrakty z JSON-a."""
from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# codegen współdzielony (w template: pakiet toolkit); tu: katalog obok harnessu
sys.path.insert(0, os.path.join(ROOT, "..", "codegen"))
import contract_codegen as cg  # noqa: E402


def load_contracts(path: str) -> dict:
    doc = json.load(open(path))
    return {route: SimpleNamespace(**{**c, "inverse_route": c.get("inverseRoute") or ""})
            for route, c in doc["contracts"].items()}


def emit(contracts_path: str) -> str:
    cg.CONTRACTS = load_contracts(contracts_path)        # zasil generator kontraktami z JSON
    header = ('# WYGENEROWANE Z contracts.json — NIE EDYTUJ RĘCZNIE.\n'
              '# Przegeneruj: `make gen`. Bramą jest ci/regen_check.py.\n'
              'from typing import Any\n\n'
              '# from .conn import conn, _ok  # zapewnione przez pakiet connectora\n\n')
    blocks = [cg.py_stub(route) for route in sorted(cg.CONTRACTS)]
    return header + "\n\n".join(blocks) + "\n"


if __name__ == "__main__":
    contracts = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "contracts.json")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "src", "handlers_generated.py")
    code = emit(contracts)
    if out == "-":
        sys.stdout.write(code)
    else:
        open(out, "w").write(code)
        print(f"napisano {out} ({code.count(chr(10))} linii)")
