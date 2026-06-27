# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Tryb enforce generatora: wygenerowany moduł JS/Go SAM SIĘ PILNUJE przez SDK.

`emit_js_module(sdk_import=...)` → moduł importuje `check`, wpieka schematy out, `ok(route, fields)`
waliduje kopertę przed zwrotem. `emit_go_module(sdk_import=...)` → pomocnik `Guard`. Domykamy
pętlę: generuj → samo-pilnuj. Bez toolchainu test się pomija (skip), nie kłamie zielenią.
"""
import json
import os
import shutil
import subprocess

import pytest

from urirun_contract.codegen import _load_contracts_json, emit_go_module, emit_js_module

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACTS = os.path.join(ROOT, "examples", "windowpair", "contracts.json")
JS_SDK = os.path.join(ROOT, "sdk", "js", "contract.mjs")
GO_SDK = os.path.join(ROOT, "sdk", "go")


@pytest.fixture(scope="module")
def contracts():
    return _load_contracts_json(CONTRACTS)


# ── kształt (bez toolchainu) ─────────────────────────────────────────────────

def test_js_enforce_mode_imports_sdk_and_self_guards(contracts):
    code = emit_js_module(contracts, sdk_import="./contract.mjs")
    assert 'import { check } from "./contract.mjs"' in code
    assert "const _OUT =" in code
    assert "export const ok = (route, fields) =>" in code
    assert 'ok("window/command/close"' in code  # stub przekazuje trasę


GO_IMPORT = "github.com/if-uri/urirun-contract/sdk/go/contract"


def test_go_enforce_mode_emits_guard(contracts):
    code = emit_go_module(contracts, sdk_import=GO_IMPORT)
    assert "contract.Check(_out[route]" in code
    assert "func Guard(route string" in code
    assert "func init()" in code


def test_default_mode_unchanged(contracts):
    """Bez sdk_import generator zachowuje stare wyjście (kompatybilność wsteczna)."""
    assert "import { check }" not in emit_js_module(contracts)
    assert "func Guard(" not in emit_go_module(contracts)


# ── runtime JS: dobra koperta przechodzi, zła rzuca ──────────────────────────

@pytest.mark.skipif(not shutil.which("node"), reason="brak node")
def test_js_self_guard_runtime(contracts, tmp_path):
    shutil.copy(JS_SDK, tmp_path / "contract.mjs")
    (tmp_path / "handlers.mjs").write_text(emit_js_module(contracts, sdk_import="./contract.mjs"))
    probe = tmp_path / "probe.mjs"
    probe.write_text(
        "import { ok } from './handlers.mjs';\n"
        "const full = {action:'window-close', reversible:true, snapshot:{}, "
        "inverse:{path:'window/command/restore', args:{snapshot:{}}}};\n"
        "let good=false, caught=false;\n"
        "try { ok('window/command/close', full); good=true; } catch(e){}\n"
        "try { ok('window/command/close', {...full, action:'WRONG'}); } catch(e){ caught=true; }\n"
        "process.exit(good && caught ? 0 : 1);\n"
    )
    r = subprocess.run(["node", str(probe)], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, f"self-guard nie zadziałał: {r.stdout}{r.stderr}"


# ── compile Go: wygenerowane handlery + SDK Guard razem ──────────────────────

@pytest.mark.skipif(not (shutil.which("go") and shutil.which("gofmt")), reason="brak go/gofmt")
def test_go_enforce_compiles_with_sdk(contracts, tmp_path):
    code = emit_go_module(contracts, sdk_import=GO_IMPORT)
    f = tmp_path / "handlers.go"
    f.write_text(code)
    fmt = subprocess.run(["gofmt", "-l", str(f)], capture_output=True, text=True)
    assert fmt.stdout.strip() == "", f"nie gofmt-clean: {fmt.stdout}"
    mod = "github.com/if-uri/urirun-contract/sdk/go"
    (tmp_path / "go.mod").write_text(
        f"module hgen\n\ngo 1.21\n\nrequire {mod} v0.0.0\n\nreplace {mod} => {GO_SDK}\n"
    )
    build = subprocess.run(["go", "build", "./..."], cwd=tmp_path, capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
