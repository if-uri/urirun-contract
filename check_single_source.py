#!/usr/bin/env python3
# Part of the ifURI solution — brama jednego źródła (single-source).
"""Wyłapuje własny anty-wzorzec projektu: kernel (gate, codegen) skopiowany do wielu miejsc.
Kontrakt rozwiązuje dryf deklaracji — ale jeśli SAMA brama jest zwendorowana ×N ręcznie, to
dryfuje tak samo. Ta brama liczy DEFINICJE wyróżniających funkcji kernela; >1 definicja = FAIL.
Re-eksport (`from urirun_contract.gate import *`) jest OK — liczą się tylko ciała, nie importy.

  python check_single_source.py <root>     # exit 1 jeśli kernel zdefiniowany w >1 pliku
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

# wyróżniające sygnatury: jeśli plik DEFINIUJE którąś, jest "kopią" danego komponentu
MARKERS = {
    "gate":    [r"^def consumer_input_check\(", r"^def check_wire\(", r"^class ContractViolation\b"],
    "codegen": [r"^def py_stub\(", r"^def go_stub\("],
}


def defines(path: str, patterns: list[str]) -> bool:
    try:
        text = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return False
    return all(re.search(p, text, re.MULTILINE) for p in patterns)


def file_hash(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:10]


def main(root: str) -> int:
    found: dict[str, list[str]] = {k: [] for k in MARKERS}
    for dp, _, files in os.walk(root):
        if "__pycache__" in dp or "/.git" in dp:
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dp, fn)
            for comp, pats in MARKERS.items():
                if defines(p, pats):
                    found[comp].append(p)

    bad = False
    for comp, paths in found.items():
        if len(paths) <= 1:
            print(f"  OK  {comp}: jedno źródło" + (f" ({paths[0]})" if paths else " (brak)"))
            continue
        bad = True
        hashes = {file_hash(p) for p in paths}
        drift = "  ⚠ JUŻ ROZJECHANE (różne hashe)" if len(hashes) > 1 else "  (na razie identyczne)"
        print(f"  FAIL {comp}: zdefiniowany w {len(paths)} plikach{drift}")
        for p in sorted(paths):
            n = sum(1 for _ in open(p, encoding="utf-8", errors="ignore"))
            print(f"         {n:>4}L  {p}  [{file_hash(p)}]")
        print(f"         → zostaw JEDNO źródło ({comp}), resztę zastąp `from urirun_contract.{comp} import *`")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
