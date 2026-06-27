#!/usr/bin/env python3
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Brama anty-dryfu: src/handlers_generated.py musi być identyczne z tym, co
wygenerowałby emit_handlers.py z aktualnego contracts.json.

Różnica = albo ktoś ręcznie zedytował generowany plik, albo zmienił kontrakt
i zapomniał przegenerować. W obu przypadkach commit jest BLOKOWANY.

Exit 0 = zgodne. Exit 1 = dryf wykryty.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from urirun_contract.codegen import _load_contracts_json, emit_py_module  # noqa: E402


def main() -> int:
    contracts_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "contracts.json")
    generated_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "src", "handlers_generated.py")

    if not os.path.exists(contracts_path):
        print(f"POMIŃ: brak {contracts_path} (nowe repo)", file=sys.stderr)
        return 0

    contracts = _load_contracts_json(contracts_path)
    fresh = emit_py_module(contracts)

    if not os.path.exists(generated_path):
        print(f"DRYF: {generated_path} nie istnieje — uruchom `make gen` i scommituj",
              file=sys.stderr)
        return 1

    committed = open(generated_path).read()
    if committed != fresh:
        print(f"DRYF: {generated_path} != generacja z contracts.json", file=sys.stderr)
        print("  uruchom `make gen` i scommituj (albo cofnij ręczną edycję generowanego pliku)",
              file=sys.stderr)
        return 1

    print(f"OK: wygenerowany kod zgodny z kontraktem (brak ręcznego dryfu)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
