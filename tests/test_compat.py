# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Brama additive-only — wariancja inp/out jest sednem, więc tu leży najwięcej przypadków.

out kowariantne: dodaj pole OK, usuń pole = breaking, ?T→T OK, T→?T = breaking.
inp kontrawariantne: dodaj OPCJONALNE OK, dodaj WYMAGANE = breaking, T→?T OK, ?T→T = breaking.
"""
import json
import os
import subprocess
import sys

import pytest

from urirun_contract.contract_compat import compare_route, incompatibilities

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(ROOT, "ci", "check_compat.py")
BASELINE = os.path.join(ROOT, "examples", "windowpair", "contracts.baseline.json")


def _doc(route, c):
    return {"contracts": {route: c}}


def _c(**kw):
    base = {"version": "v1", "effect": "command", "reversible": False,
            "inp": {}, "out": {}, "errors": []}
    base.update(kw)
    return base


def _kinds(changes, where=None):
    return {(c.field, c.kind) for c in changes if where is None or c.where == where}


# ── OUT (kowariantne) ────────────────────────────────────────────────────────

def test_out_add_field_is_additive():
    old, new = _c(out={"a": "str"}), _c(out={"a": "str", "b": "int"})
    assert ("b", "additive") in _kinds(compare_route("r", old, new), "out")
    assert incompatibilities(_doc("r", old), _doc("r", new)) == []


def test_out_remove_field_is_breaking():
    old, new = _c(out={"a": "str", "b": "int"}), _c(out={"a": "str"})
    assert ("b", "breaking") in _kinds(compare_route("r", old, new), "out")
    assert len(incompatibilities(_doc("r", old), _doc("r", new))) == 1


def test_out_weaken_required_to_optional_is_breaking():
    old, new = _c(out={"a": "str"}), _c(out={"a": "?str"})
    assert ("a", "breaking") in _kinds(compare_route("r", old, new), "out")


def test_out_strengthen_optional_to_required_is_additive():
    old, new = _c(out={"a": "?str"}), _c(out={"a": "str"})
    assert ("a", "additive") in _kinds(compare_route("r", old, new), "out")
    assert incompatibilities(_doc("r", old), _doc("r", new)) == []


# ── INP (kontrawariantne) ────────────────────────────────────────────────────

def test_inp_add_required_is_breaking():
    old, new = _c(inp={"a": "str"}), _c(inp={"a": "str", "b": "int"})
    assert ("b", "breaking") in _kinds(compare_route("r", old, new), "inp")


def test_inp_add_optional_is_additive():
    old, new = _c(inp={"a": "str"}), _c(inp={"a": "str", "b": "?int"})
    assert ("b", "additive") in _kinds(compare_route("r", old, new), "inp")
    assert incompatibilities(_doc("r", old), _doc("r", new)) == []


def test_inp_relax_required_to_optional_is_additive():
    old, new = _c(inp={"a": "str"}), _c(inp={"a": "?str"})
    assert ("a", "additive") in _kinds(compare_route("r", old, new), "inp")


def test_inp_tighten_optional_to_required_is_breaking():
    old, new = _c(inp={"a": "?str"}), _c(inp={"a": "str"})
    assert ("a", "breaking") in _kinds(compare_route("r", old, new), "inp")


def test_inp_remove_field_is_additive():
    old, new = _c(inp={"a": "str", "b": "int"}), _c(inp={"a": "str"})
    assert ("b", "additive") in _kinds(compare_route("r", old, new), "inp")


# ── meta + typy ──────────────────────────────────────────────────────────────

def test_type_change_is_breaking_both_sides():
    assert ("a", "breaking") in _kinds(compare_route("r", _c(out={"a": "str"}), _c(out={"a": "int"})), "out")
    assert ("a", "breaking") in _kinds(compare_route("r", _c(inp={"a": "str"}), _c(inp={"a": "int"})), "inp")


def test_effect_change_is_breaking():
    old, new = _c(effect="command"), _c(effect="query")
    assert any(c.kind == "breaking" and c.where == "effect" for c in compare_route("r", old, new))


def test_reversible_drop_is_breaking_add_is_additive():
    drop = compare_route("r", _c(reversible=True), _c(reversible=False))
    add = compare_route("r", _c(reversible=False), _c(reversible=True))
    assert any(c.kind == "breaking" for c in drop)
    assert all(c.kind == "additive" for c in add if c.where == "reversible")


def test_error_class_remove_breaking_add_additive():
    rm = compare_route("r", _c(errors=["unreachable"]), _c(errors=[]))
    ad = compare_route("r", _c(errors=[]), _c(errors=["unreachable"]))
    assert ("unreachable", "breaking") in _kinds(rm, "errors")
    assert ("unreachable", "additive") in _kinds(ad, "errors")


# ── bramka wersji ────────────────────────────────────────────────────────────

def test_version_bump_allows_breaking():
    old = _c(version="v1", out={"a": "str", "b": "int"})
    new = _c(version="v2", out={"a": "str"})  # usunięte pole, ale bump v1→v2
    assert incompatibilities(_doc("r", old), _doc("r", new)) == []


def test_removed_route_is_breaking():
    old = {"contracts": {"r1": _c(), "r2": _c()}}
    new = {"contracts": {"r1": _c()}}
    bad = incompatibilities(old, new)
    assert len(bad) == 1 and bad[0].where == "route"


def test_added_route_is_fine():
    old = {"contracts": {"r1": _c()}}
    new = {"contracts": {"r1": _c(), "r2": _c()}}
    assert incompatibilities(old, new) == []


def test_nested_object_recursion():
    old = _c(out={"inverse": {"path": "str", "args": "obj"}})
    new = _c(out={"inverse": {"path": "str"}})  # usunięte zagnieżdżone pole
    assert any(c.field == "inverse.args" and c.kind == "breaking"
               for c in compare_route("r", old, new))


# ── CLI brama (end-to-end) ───────────────────────────────────────────────────

@pytest.mark.skipif(not os.path.exists(BASELINE), reason="brak zamrożonego baseline")
def test_cli_passes_on_identical_contract():
    current = os.path.join(ROOT, "examples", "windowpair", "contracts.json")
    r = subprocess.run([sys.executable, CLI, BASELINE, current], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_cli_blocks_breaking_change(tmp_path):
    base = json.load(open(BASELINE)) if os.path.exists(BASELINE) else \
        {"contracts": {"r": _c(out={"a": "str", "b": "int"})}}
    bpath = tmp_path / "baseline.json"
    bpath.write_text(json.dumps(base))
    broken = json.loads(json.dumps(base))
    route = next(iter(broken["contracts"]))
    broken["contracts"][route]["out"].popitem()  # usuń jakieś pole out → breaking
    cpath = tmp_path / "current.json"
    cpath.write_text(json.dumps(broken))
    r = subprocess.run([sys.executable, CLI, str(bpath), str(cpath)], capture_output=True, text=True)
    assert r.returncode == 1
    assert "NIEKOMPATYBILNE" in r.stderr


def test_cli_skips_when_no_baseline(tmp_path):
    missing = tmp_path / "nope.json"
    current = tmp_path / "c.json"
    current.write_text(json.dumps({"contracts": {}}))
    r = subprocess.run([sys.executable, CLI, str(missing), str(current)], capture_output=True, text=True)
    assert r.returncode == 0 and "POMIŃ" in r.stderr
