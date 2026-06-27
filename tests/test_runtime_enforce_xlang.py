# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Runtime enforce w 3 językach z JEDNEGO contracts.json — parytet guarda koperty.

SDK Python/JS/Go waliduje tę samą złotą kopertę (→ brak naruszenia) i ten sam fixture dryfu
(bool serializowany jako string łamie const:true → naruszenie). To dowód, że guard jest
językowo-neutralny: connector w dowolnym języku nie może po cichu skłamać o kontrakcie.
JS/Go pomijane (skip), gdy brak toolchainu — nie kłamią zielenią.
"""
import json
import os
import shutil
import subprocess

import pytest

from urirun_contract import Contract, envelope_violation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACTS = os.path.join(ROOT, "examples", "windowpair", "contracts.json")
JS = os.path.join(ROOT, "sdk", "js", "contract.mjs")
GO_DIR = os.path.join(ROOT, "sdk", "go")
ROUTE = "window/command/close"

_DOC = json.load(open(CONTRACTS))


def _contract(route: str) -> Contract:
    d = _DOC["contracts"][route]
    return Contract(
        version=d["version"], effect=d["effect"], reversible=d["reversible"],
        inverse_route=d.get("inverseRoute", ""), inp=d["inp"], out=d["out"],
        errors=tuple(d["errors"]), examples=tuple(d["examples"]),
    )


def _golden_ok(route: str) -> dict:
    for ex in _DOC["contracts"][route]["examples"]:
        if ex["result"].get("ok"):
            return dict(ex["result"])
    raise AssertionError("brak złotej koperty ok")


def _drift(route: str) -> dict:
    """Koperta z bool zserializowanym jako string — łamie const:true (jak peer --lie)."""
    env = _golden_ok(route)
    env["reversible"] = "true"  # bool → "true" (string)
    return env


def _run_cli(cmd: list[str], envelope: dict, cwd: str | None = None) -> tuple[int, str]:
    r = subprocess.run(cmd, input=json.dumps(envelope), capture_output=True,
                       text=True, cwd=cwd)
    return r.returncode, (r.stdout + r.stderr).strip()


# ── Python (kernel, źródło prawdy) ───────────────────────────────────────────

def test_python_accepts_golden_and_catches_drift():
    c = _contract(ROUTE)
    assert envelope_violation(c, _golden_ok(ROUTE)) is None
    assert envelope_violation(c, _drift(ROUTE)) is not None


# ── JS SDK ───────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not shutil.which("node"), reason="brak node")
def test_js_accepts_golden_and_catches_drift():
    base = ["node", JS, CONTRACTS, ROUTE]
    code_ok, out_ok = _run_cli(base, _golden_ok(ROUTE))
    assert code_ok == 0 and out_ok == "OK", out_ok
    code_d, out_d = _run_cli(base, _drift(ROUTE))
    assert code_d == 1 and out_d.startswith("VIOLATION"), out_d


# ── Go SDK ───────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not shutil.which("go"), reason="brak go")
def test_go_accepts_golden_and_catches_drift():
    base = ["go", "run", "./cmd/enforce", CONTRACTS, ROUTE]
    code_ok, out_ok = _run_cli(base, _golden_ok(ROUTE), cwd=GO_DIR)
    assert code_ok == 0 and out_ok == "OK", out_ok
    code_d, out_d = _run_cli(base, _drift(ROUTE), cwd=GO_DIR)
    assert code_d == 1 and out_d.startswith("VIOLATION"), out_d
