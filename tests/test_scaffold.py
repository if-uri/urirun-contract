# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Szkielet kontraktu z manifestu/kodu — adopcja floty generacją, nie ręką.

Kluczowy dowód: wygenerowany szkielet KONFORMUJE (przez kernel `conform`) — jest poprawnym
punktem zaczepienia do edycji, nie śmieciem. `scaffold_gaps` mówi, co człowiek ma dopisać.
"""
from urirun_contract import Contract, conform
from urirun_contract.contract_scaffold import (
    contracts_from_manifest, contracts_from_routes, discover_routes,
    effect_of, route_key, scaffold_gaps,
)


# ── odkrywanie tras ──────────────────────────────────────────────────────────

def test_discover_routes_from_handler_decorators():
    src = (
        '@conn.handler("inbox/query/list", isolated=True)\n'
        'def list_inbox(): ...\n'
        "@conn.command('message/command/send')\n"
        'def send(): ...\n'
        '@conn.query("message/query/read")\n'
    )
    assert discover_routes(src) == ["inbox/query/list", "message/command/send", "message/query/read"]


def test_discover_routes_dedupes_preserving_order():
    src = '@conn.handler("a/query/x")\n@conn.handler("a/query/x")\n@conn.handler("b/command/y")\n'
    assert discover_routes(src) == ["a/query/x", "b/command/y"]


def test_route_key_strips_scheme_but_not_bare():
    assert route_key("hash://host/text/query/sha256") == "text/query/sha256"
    assert route_key("message/command/send") == "message/command/send"  # już klucz


def test_effect_from_verb():
    assert effect_of("message/command/send") == "command"
    assert effect_of("inbox/query/list") == "query"


# ── budowa szkieletu ─────────────────────────────────────────────────────────

def test_manifest_scaffold_infers_input_and_effect():
    manifest = {
        "routes": ["hash://host/text/query/sha256"],
        "examples": [{"uri": "hash://host/text/query/sha256", "payload": {"text": "hello"}}],
    }
    doc = contracts_from_manifest(manifest)
    c = doc["contracts"]["text/query/sha256"]
    assert c["effect"] == "query"
    assert c["inp"] == {"text": "str"}
    assert c["out"] == {}  # celowo puste — do uzupełnienia
    assert c["examples"] == [{"payload": {"text": "hello"}}]


def test_input_optional_when_not_in_all_examples():
    doc = contracts_from_routes(
        ["x/query/y"],
        {"x/query/y": [{"payload": {"a": "1", "b": 2}}, {"payload": {"a": "2"}}]},
    )
    inp = doc["contracts"]["x/query/y"]["inp"]
    assert inp["a"] == "str"      # w obu → wymagane
    assert inp["b"] == "?int"     # tylko w jednym → opcjonalne


def test_scaffold_gaps_flags_empty_out_and_missing_result():
    doc = contracts_from_routes(["m/command/send"], {})
    gaps = scaffold_gaps(doc)
    assert any("pusty `out`" in g for g in gaps)
    assert any("reversible" in g for g in gaps)  # command bez reversible


# ── KLUCZOWY DOWÓD: szkielet konformuje ──────────────────────────────────────

def _to_contracts(doc):
    return {r: Contract(version=c["version"], effect=c["effect"], reversible=c["reversible"],
                        inp=c["inp"], out=c["out"], errors=tuple(c["errors"]),
                        examples=tuple(c["examples"]))
            for r, c in doc["contracts"].items()}


def test_scaffold_conforms():
    """Szkielet z realistycznego zestawu tras przechodzi `conform` (poprawny punkt startowy)."""
    doc = contracts_from_routes(
        ["inbox/query/list", "message/command/send"],
        {"message/command/send": [{"payload": {"to": "a@b", "body": "hi"}}]},
    )
    conform(_to_contracts(doc))  # nie rzuca = konformuje
