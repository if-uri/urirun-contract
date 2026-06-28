# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Example contracts must be portable across the contract toolchain.

This is the shared example harness for the new connector+contract shape:

    contracts.json -> Contract -> conform -> JSON Schema -> codegen

It intentionally scans example folders instead of hard-coding one route. A new example that adds a
neutral ``contracts.json`` should immediately get the same portability guarantees.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from urirun_contract import Contract, conform
from urirun_contract.codegen import _load_contracts_json, emit_go_module, emit_js_module, emit_py_module
from urirun_contract.contract_jsonschema import to_json_schema_document

jsonschema = pytest.importorskip("jsonschema")

ROOT = Path(__file__).resolve().parents[1]
IF_URI_ROOT = ROOT.parent


def _example_contract_files() -> list[Path]:
    paths: list[Path] = []
    paths.extend(sorted((ROOT / "examples").glob("*/contracts.json")))
    paths.extend(sorted((IF_URI_ROOT / "examples").glob("*/contracts.json")))
    return [p for p in paths if p.is_file()]


EXAMPLE_CONTRACTS = _example_contract_files()


def _contract(c: dict) -> Contract:
    return Contract(
        version=c.get("version", "v1"),
        effect=c.get("effect", "query"),
        reversible=bool(c.get("reversible", False)),
        inverse_route=c.get("inverseRoute") or "",
        inp=c.get("inp", {}),
        out=c.get("out", {}),
        errors=tuple(c.get("errors", ())),
        examples=tuple(c.get("examples", ())),
    )


@pytest.mark.parametrize("path", EXAMPLE_CONTRACTS, ids=lambda p: str(p.relative_to(IF_URI_ROOT)))
def test_example_contracts_conform(path: Path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc.get("contracts"), f"{path} has no contracts"
    conform({route: _contract(c) for route, c in doc["contracts"].items()})


@pytest.mark.parametrize("path", EXAMPLE_CONTRACTS, ids=lambda p: str(p.relative_to(IF_URI_ROOT)))
def test_example_contracts_json_schema_validates_golden_examples(path: Path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    for route, c in doc["contracts"].items():
        in_schema = to_json_schema_document(route, c.get("inp", {}), kind="input",
                                            version=c.get("version", "v1"))
        out_schema = to_json_schema_document(route, c.get("out", {}), kind="output",
                                             version=c.get("version", "v1"))
        jsonschema.Draft202012Validator.check_schema(in_schema)
        jsonschema.Draft202012Validator.check_schema(out_schema)
        for i, example in enumerate(c.get("examples", [])):
            where = f"{path}:{route}:examples[{i}]"
            jsonschema.validate(example.get("payload", {}), in_schema), where
            jsonschema.validate(example.get("result", {}), out_schema), where


@pytest.mark.parametrize("path", EXAMPLE_CONTRACTS, ids=lambda p: str(p.relative_to(IF_URI_ROOT)))
def test_example_contracts_drive_polyglot_codegen(path: Path):
    contracts = _load_contracts_json(str(path))
    routes = set(json.loads(path.read_text(encoding="utf-8"))["contracts"])

    py_code = emit_py_module(contracts)
    compile(py_code, f"{path.name}.handlers_generated.py", "exec")
    assert {line.split('"')[1] for line in py_code.splitlines()
            if line.startswith("@conn.handler(")} == routes

    js_code = emit_js_module(contracts)
    go_code = emit_go_module(contracts)
    assert js_code.count("export function ") == len(routes)
    assert go_code.count("func ") == len(routes)
    for route in routes:
        assert route in js_code
        assert route in go_code
