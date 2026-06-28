# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Smoke: KAŻDY moduł kernela importuje się (łapie SyntaxError zanim zepsuje cały tor).

Geneza (P0.3): literówka w f-stringu `contract_scaffold.py` (polski cudzysłów „…" z ASCII `"`)
dała `SyntaxError` przy imporcie, który wywrócił WSZYSTKIE testy importujące kernel transytywnie —
z mylącym tracebackiem. Ten test importuje każdy moduł osobno: pierwszy z błędem składni czerwienieje
JAWNIE, z nazwą modułu, zamiast kaskady niezwiązanych awarii. Trzyma też listę modułów w zgodzie
z `check_single_source` (każdy komponent kernela = jeden moduł)."""
import importlib

import pytest

# Każdy komponent kernela (1:1 z MARKERS w check_single_source.py) + brama single-source.
KERNEL_MODULES = [
    "urirun_contract",                       # pakiet (re-eksport publicznego API)
    "urirun_contract.gate",
    "urirun_contract.codegen",
    "urirun_contract.contract_jsonschema",
    "urirun_contract.contract_lint",
    "urirun_contract.contract_reversible",
    "urirun_contract.contract_compat",
    "urirun_contract.contract_scaffold",
    "urirun_contract.contract_export",
    "urirun_contract.contract_typescript",
    "urirun_contract.check_single_source",
]


@pytest.mark.parametrize("module", KERNEL_MODULES)
def test_kernel_module_imports(module):
    importlib.import_module(module)  # SyntaxError/ImportError → ten test (nazwa modułu w id) czerwony


def test_smoke_covers_every_kernel_module():
    """Lista smoke nie może się rozjechać z plikami `urirun_contract/*.py` (poza __init__/prywatne)."""
    import os
    pkg_dir = os.path.dirname(importlib.import_module("urirun_contract").__file__)
    on_disk = {
        f"urirun_contract.{name[:-3]}"
        for name in os.listdir(pkg_dir)
        if name.endswith(".py") and name != "__init__.py" and not name.startswith("_")
    }
    covered = set(KERNEL_MODULES) - {"urirun_contract"}
    missing = on_disk - covered
    assert not missing, f"smoke nie obejmuje modułów kernela: {sorted(missing)} — dopisz do KERNEL_MODULES"
