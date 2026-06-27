# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Emitter JSON Schema: kontrakt → standardowy dokument draft 2020-12, walidujący golden corpus.

Złote przykłady kontraktu robią podwójną robotę: tu są wektorem testowym dla SCHEMATU —
payload ok musi przejść input-schema, result ok musi przejść output-schema. Jeśli mapper
dialektu zdryfuje, golden przestanie walidować.
"""
import json
import os

import pytest

from urirun_contract.contract_jsonschema import to_json_schema, to_json_schema_document

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACTS = os.path.join(ROOT, "examples", "windowpair", "contracts.json")
DOC = json.load(open(CONTRACTS))

jsonschema = pytest.importorskip("jsonschema")


def _contracts():
    return DOC["contracts"]


def test_document_has_standard_metadata():
    c = _contracts()["window/command/close"]
    doc = to_json_schema_document("window/command/close", c["inp"], kind="input", version="v1")
    assert doc["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert doc["$id"] == "urn:urirun:contract:window.command.close:input"
    assert doc["x-contractVersion"] == "v1"


@pytest.mark.parametrize("route", list(DOC["contracts"]))
def test_emitted_schemas_are_valid_jsonschema(route):
    c = _contracts()[route]
    for kind, key in (("input", "inp"), ("output", "out")):
        doc = to_json_schema_document(route, c.get(key, {}), kind=kind)
        jsonschema.Draft202012Validator.check_schema(doc)  # sam schemat poprawny


@pytest.mark.parametrize("route", list(DOC["contracts"]))
def test_golden_examples_validate_against_schema(route):
    c = _contracts()[route]
    in_schema = to_json_schema_document(route, c.get("inp", {}), kind="input")
    out_schema = to_json_schema_document(route, c.get("out", {}), kind="output")
    for ex in c.get("examples", []):
        if not ex.get("result", {}).get("ok"):
            continue
        jsonschema.validate(ex.get("payload", {}), in_schema)
        jsonschema.validate(ex["result"], out_schema)


def test_optional_field_is_not_required():
    # inp {"id": "?str"} → pole opcjonalne, brak w required, pusty payload waliduje
    doc = to_json_schema("?str")
    assert doc == {"type": "string"}
    in_schema = to_json_schema_document("window/command/close", {"id": "?str"}, kind="input")
    assert "required" not in in_schema
    jsonschema.validate({}, in_schema)
