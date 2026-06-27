# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Polyglot SDK: jeden contracts.json → kompletny moduł szkieletów w Pythonie, JS i Go.

Determinizm + realność: wygenerowany JS musi przejść `node --check`, wygenerowany Go
musi się skompilować (`go build`) i być gofmt-clean. Bez działającego toolchainu test się
pomija (skip), nie kłamie zielenią.
"""
import json
import os
import shutil
import subprocess

import pytest

from urirun_contract.codegen import (
    _load_contracts_json, emit_go_module, emit_js_module, emit_py_module,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACTS = os.path.join(ROOT, "examples", "windowpair", "contracts.json")
ROUTES = list(json.load(open(CONTRACTS))["contracts"])


@pytest.fixture(scope="module")
def contracts():
    return _load_contracts_json(CONTRACTS)


def test_py_module_compiles(contracts):
    code = emit_py_module(contracts)
    compile(code, "handlers_generated.py", "exec")  # składnia Pythona OK
    for route in ROUTES:
        assert route in code


def test_js_module_has_function_per_route(contracts):
    code = emit_js_module(contracts)
    assert code.count("export function ") == len(ROUTES)
    assert "const ok =" in code


def test_go_module_has_struct_and_func_per_route(contracts):
    code = emit_go_module(contracts)
    assert code.startswith("// WYGENEROWANE")
    assert "package handlers" in code
    assert code.count("func ") == len(ROUTES)
    assert code.count("In struct {") == len(ROUTES)


@pytest.mark.skipif(not shutil.which("node"), reason="brak node — pomijam realny parse JS")
def test_js_module_parses_with_node(contracts, tmp_path):
    f = tmp_path / "handlers_generated.mjs"
    f.write_text(emit_js_module(contracts))
    r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.mark.skipif(not (shutil.which("go") and shutil.which("gofmt")),
                    reason="brak go/gofmt — pomijam realną kompilację Go")
def test_go_module_compiles_and_is_gofmt_clean(contracts, tmp_path):
    (tmp_path / "go.mod").write_text("module hgen\n\ngo 1.21\n")
    f = tmp_path / "handlers_generated.go"
    f.write_text(emit_go_module(contracts))
    fmt = subprocess.run(["gofmt", "-l", str(f)], capture_output=True, text=True)
    assert fmt.stdout.strip() == "", f"nie gofmt-clean: {fmt.stdout}"
    build = subprocess.run(["go", "build", "./..."], cwd=tmp_path, capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
