# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Anty-drift kernela: shim toolkit re-eksportuje DOKŁADNIE publiczne API pakietu — te same obiekty.

Kontrakt usuwa dryf deklaracji handlerów; ten test usuwa dryf SAMEJ bramy. Gdyby ktoś:
  • zwendorował kopię kernela (drugą definicję `check`/`to_json_schema`/...),
  • rozjechał shim z `urirun_contract.__all__` (brak nowej funkcji / przeciek helpera),
  • podmienił re-eksport na własną, rozjechaną implementację,
ten test czerwienieje. `is`-tożsamość obiektu = ta sama implementacja, nie kopia → zero dryfu zachowania.

Oracle z preview: public_api(shim) == public_api(pkg) ∧ behavior(shim) == behavior(pkg).
"""
import ast
import os
import subprocess
import sys

import urirun_contract as pkg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHIM = os.path.join(ROOT, "toolkit", "contract_gate.py")
PUBLIC = set(pkg.__all__)


def _load_shim():
    sys.path.insert(0, os.path.join(ROOT, "toolkit"))
    import contract_gate  # noqa: PLC0415
    return contract_gate


def _explicit_names() -> set:
    """Nazwy z jawnych `from urirun_contract import (...)` w shimie (pomija gwiazdkę)."""
    names = set()
    for node in ast.walk(ast.parse(open(SHIM).read())):
        if isinstance(node, ast.ImportFrom):
            names |= {a.name for a in node.names if a.name != "*"}
    return names


def test_shim_reexports_full_public_api():
    shim = _load_shim()
    missing = sorted(n for n in PUBLIC if not hasattr(shim, n))
    assert not missing, f"shim nie re-eksportuje publicznych nazw: {missing}"


def test_shim_symbols_are_identical_objects():
    """Tożsamość obiektu = ta SAMA implementacja kernela, nie zwendorowana kopia."""
    shim = _load_shim()
    notsame = sorted(n for n in PUBLIC if getattr(shim, n) is not getattr(pkg, n))
    assert not notsame, f"shim ma własne (rozjechane) obiekty dla: {notsame}"


def test_explicit_ide_list_equals_public_api():
    """Lista jawna dla IDE musi być == __all__ — inaczej type-checker widzi inne API niż runtime."""
    explicit = _explicit_names()
    assert explicit == PUBLIC, (
        f"explicit != __all__: brakuje {sorted(PUBLIC - explicit)}, "
        f"nadmiar {sorted(explicit - PUBLIC)}"
    )


def test_shim_exposes_only_public_api():
    """`from urirun_contract import *` (pakiet ma __all__) nie może przeciekać helperów/stdlib."""
    shim = _load_shim()
    extra = sorted(n for n in dir(shim) if not n.startswith("_") and n not in PUBLIC)
    assert not extra, f"shim wystawia nadmiarowe (przeciekłe) nazwy: {extra}"


def test_single_source_guard_passes_in_default_lane():
    """Brama jednego źródła kernela biega też w pytest, nie tylko w `make single-source`."""
    r = subprocess.run(
        [sys.executable, "-m", "urirun_contract.check_single_source", ROOT],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"kernel zwendorowany w >1 miejscu:\n{r.stdout}\n{r.stderr}"
