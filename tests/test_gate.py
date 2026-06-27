# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Standalone gate tests — no urirun dependency required."""
import pytest
from urirun_contract import (
    Contract, Wire,
    check, conform, check_wire,
    wire_payload, consumer_input_check, dig,
    envelope_violation,
)


# ── minimal contracts for testing ────────────────────────────────────────────
QUERY = Contract(
    version="v1", effect="query",
    inp={"target": "str", "limit": "?int"},
    out={"kind": "const:result", "items": "list", "count": "int"},
    examples=(
        {"payload": {"target": "x"}, "result": {"ok": True, "kind": "result", "items": [], "count": 0}},
    ),
)

WRITE = Contract(
    version="v1", effect="command", reversible=True,
    inverse_route="undo/command/write",
    inp={"path": "str", "content": "str"},
    out={"action": "const:write", "bytes": "int", "path": "str", "inverse": "?obj"},
    errors=("unreachable",),
    examples=(
        {"payload": {"path": "/a", "content": "x"},
         "result": {"ok": True, "action": "write", "bytes": 1, "path": "/a",
                    "inverse": {"path": "undo/command/write", "args": {"path": "/a", "content": "x"}}}},
    ),
)

UNDO = Contract(
    version="v1", effect="command", reversible=True,
    inverse_route="data/command/write",
    inp={"path": "str", "content": "str"},   # two required — lets PARTIAL_WIRE cover only one
    out={"action": "const:undo-write", "restored": "bool"},
    examples=(
        {"payload": {"path": "/a", "content": "x"},
         "result": {"ok": True, "action": "undo-write", "restored": True}},
    ),
)

CONTRACTS = {
    "data/query/search": QUERY,
    "data/command/write": WRITE,
    "undo/command/write": UNDO,
}

WIRE = Wire("data/command/write", "undo/command/write", {"path": "path"}, note="rollback path")
PARTIAL_WIRE = Wire("data/command/write", "undo/command/write",
                    {"path": "path"},          # only path — not content → partial
                    note="partial")


# ── check() ──────────────────────────────────────────────────────────────────
class TestCheck:
    def test_str(self):
        check("str", "hello", "x")

    def test_int_not_bool(self):
        with pytest.raises(AssertionError):
            check("int", True, "x")

    def test_optional_none(self):
        check("?str", None, "x")

    def test_optional_present(self):
        check("?str", "ok", "x")

    def test_const_true(self):
        check("const:true", True, "x")

    def test_const_literal(self):
        check("const:write", "write", "x")

    def test_enum(self):
        check("enum:a|b|c", "b", "x")
        with pytest.raises(AssertionError):
            check("enum:a|b|c", "d", "x")

    def test_oneof(self):
        schema = {"oneOf": [{"kind": "const:a", "n": "int"}, {"kind": "const:b", "s": "str"}]}
        check(schema, {"kind": "a", "n": 1}, "x")
        check(schema, {"kind": "b", "s": "hi"}, "x")
        with pytest.raises(AssertionError):
            check(schema, {"kind": "c"}, "x")

    def test_list_homogeneous(self):
        check(["int"], [1, 2, 3], "x")
        with pytest.raises(AssertionError):
            check(["int"], [1, "two"], "x")

    def test_missing_required(self):
        with pytest.raises(AssertionError, match="missing required key"):
            check({"a": "str", "b": "int"}, {"a": "ok"}, "x")

    def test_optional_key_absent_ok(self):
        check({"a": "str", "b": "?int"}, {"a": "ok"}, "x")


# ── conform() ────────────────────────────────────────────────────────────────
class TestConform:
    def test_clean(self):
        conform(CONTRACTS)  # must not raise

    def test_effect_verb_mismatch(self):
        bad = {"bad/query/route": Contract(effect="command",
                                           examples=({"payload": {}, "result": {"ok": True}},))}
        with pytest.raises(AssertionError, match="contradicts"):
            conform(bad)

    def test_missing_inverse(self):
        bad = {"cmd/command/x": Contract(effect="command", reversible=True,
                                         inverse_route="cmd/command/y",
                                         examples=({"payload": {}, "result": {"ok": True}},))}
        with pytest.raises(AssertionError, match="not a declared contract"):
            conform(bad)

    def test_inverse_args_checked(self):
        # inverse.args must satisfy the inverse route's inp
        write = Contract(
            effect="command", reversible=True, inverse_route="a/command/undo",
            inp={"path": "str"}, out={"action": "const:write", "inverse": "?obj"},
            examples=({"payload": {"path": "/a"},
                        "result": {"ok": True, "action": "write",
                                   "inverse": {"path": "a/command/undo", "args": {"wrong_key": 1}}}},),
        )
        undo = Contract(
            effect="command", reversible=True, inverse_route="a/command/write",
            inp={"path": "str"}, out={"action": "const:undo"},
            examples=({"payload": {"path": "/a"}, "result": {"ok": True, "action": "undo"}},),
        )
        with pytest.raises(AssertionError, match="missing required key"):
            conform({"a/command/write": write, "a/command/undo": undo})


# ── envelope_violation() ─────────────────────────────────────────────────────
class TestEnvelopeViolation:
    def test_ok_conforms(self):
        assert envelope_violation(WRITE, {"ok": True, "action": "write", "bytes": 5, "path": "/a"}) is None

    def test_ok_wrong_type(self):
        v = envelope_violation(WRITE, {"ok": True, "action": "write", "bytes": "five"})
        assert v is not None

    def test_error_declared_class_ok(self):
        env = {"ok": False, "remediation": {"class": "unreachable"}}
        assert envelope_violation(WRITE, env) is None

    def test_error_undeclared_class(self):
        env = {"ok": False, "remediation": {"class": "route-missing"}}
        v = envelope_violation(WRITE, env)
        assert v is not None and "route-missing" in v


# ── Wire + check_wire() ───────────────────────────────────────────────────────
class TestWire:
    def test_clean_wire(self):
        assert check_wire(WIRE, CONTRACTS) == []

    def test_type_mismatch(self):
        bad = Wire("data/query/search", "data/command/write",
                   {"path": "count"},  # count is int, path needs str
                   note="bad")
        probs = check_wire(bad, CONTRACTS)
        assert any("nie pasuje" in p for p in probs)

    def test_missing_path(self):
        bad = Wire("data/query/search", "data/command/write",
                   {"path": "does.not.exist"}, note="bad")
        probs = check_wire(bad, CONTRACTS)
        assert any("ścieżki" in p for p in probs)

    def test_partial_wire_reported(self):
        payload = wire_payload(PARTIAL_WIRE, {"ok": True, "kind": "result", "items": [], "count": 0})
        mode, _ = consumer_input_check(UNDO, payload, PARTIAL_WIRE)
        assert mode == "partial"

    def test_full_wire_reported(self):
        envelope = {"ok": True, "action": "write", "bytes": 3, "path": "/x",
                    "inverse": {"path": "undo/command/write", "args": {"path": "/x", "content": "x"}}}
        # wire carries BOTH required fields → full handoff
        w = Wire("data/command/write", "undo/command/write", {"path": "path", "content": "bytes"})
        payload = wire_payload(w, envelope)
        mode, _ = consumer_input_check(UNDO, payload, w)
        assert mode == "full"


# ── dig() ─────────────────────────────────────────────────────────────────────
class TestDig:
    def test_simple(self):
        assert dig({"a": {"b": 1}}, "a.b") == 1

    def test_list_index(self):
        assert dig({"dims": [1920, 1080]}, "dims.0") == 1920

    def test_missing(self):
        with pytest.raises(KeyError):
            dig({"a": 1}, "b")
