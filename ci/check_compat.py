#!/usr/bin/env python3
# Part of the ifURI solution — brama wstecznej kompatybilności (additive-only per trasa).
"""Porównuje OBECNY contracts.json z zamrożonym BASELINE: zmiana trasy przy tej samej wersji
musi być wstecznie kompatybilna. Zmiana łamiąca bez bumpa wersji = commit BLOKOWANY.

Importuje klasyfikator z urirun_contract (jedyne źródło — nie przepisuj tu reguł wariancji).

  python ci/check_compat.py <baseline.json> <current.json>   # exit 1 jeśli łamiące zmiany
  python ci/check_compat.py                                   # domyślne ścieżki windowpair

Świadoma zmiana łamiąca: bump `version` trasy (v1→v2) ALBO przemroź baseline (`make freeze`).
Brak baseline = POMIŃ (pierwsze wydanie) — jak regen_check.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from urirun_contract.contract_compat import incompatibilities  # noqa: E402

_CONTRACTS = os.path.join(ROOT, "examples", "windowpair", "contracts.json")
_BASELINE = os.path.join(ROOT, "examples", "windowpair", "contracts.baseline.json")


def main(argv: list[str]) -> int:
    baseline_path = argv[0] if argv else _BASELINE
    current_path = argv[1] if len(argv) > 1 else _CONTRACTS

    if not os.path.exists(baseline_path):
        print(f"POMIŃ: brak baseline {baseline_path} — pierwsze wydanie (uruchom `make freeze`)",
              file=sys.stderr)
        return 0

    old = json.load(open(baseline_path))
    new = json.load(open(current_path))
    bad = incompatibilities(old, new)
    if not bad:
        print(f"OK: zmiany wstecznie kompatybilne (additive-only) vs {os.path.basename(baseline_path)}")
        return 0

    print(f"NIEKOMPATYBILNE: {len(bad)} zmian łamiących bez bumpa wersji:", file=sys.stderr)
    for c in bad:
        print(f"  ✗ {c.route} [{c.where}] {c.field}: {c.detail}", file=sys.stderr)
    print("  → bumpnij `version` trasy (v1→v2) albo przemroź baseline (`make freeze`) "
          "jeśli zmiana jest świadoma", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
