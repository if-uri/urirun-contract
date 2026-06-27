#!/usr/bin/env python3
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Deterministyczny generator: contracts.json → src/handlers_generated.py.

Sygnatura + kształt koperty pochodzi z kontraktu. Człowiek/LLM uzupełnia TYLKO ciało.

  python ci/emit_handlers.py                                  # contracts.json → src/handlers_generated.py
  python ci/emit_handlers.py path/to/contracts.json           # inny plik wejściowy
  python ci/emit_handlers.py contracts.json - > out.py        # stdout
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from urirun_contract.codegen import _load_contracts_json, emit_py_module  # noqa: E402


def main() -> int:
    contracts_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "contracts.json")
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "src", "handlers_generated.py")

    if not os.path.exists(contracts_path):
        print(f"BŁĄD: brak {contracts_path}", file=sys.stderr)
        return 1

    contracts = _load_contracts_json(contracts_path)
    code = emit_py_module(contracts)

    if out_path == "-":
        sys.stdout.write(code)
    else:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        open(out_path, "w").write(code)
        print(f"napisano {out_path} ({code.count(chr(10))} linii)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
