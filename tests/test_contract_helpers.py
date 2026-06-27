from urirun_contract import Contract, callspec_fields, lint_handler_signatures, to_json_schema


def test_to_json_schema_projects_contract_dialect():
    schema = to_json_schema({
        "ok": "const:true",
        "path": "str",
        "n": "int",
        "note": "?str",
        "variants": {"oneOf": [{"kind": "const:a"}, {"kind": "const:b", "count": "int"}]},
    })

    assert schema["type"] == "object"
    assert schema["properties"]["ok"] == {"const": True}
    assert schema["properties"]["n"] == {"type": "integer"}
    assert "note" not in schema["required"]
    assert "oneOf" in schema["properties"]["variants"]


def test_lint_handler_signatures_detects_missing_and_mistyped_fields():
    contracts = {
        "demo/query/read": Contract(inp={"path": "str", "limit": "int"}),
    }
    bindings_doc = {
        "bindings": {
            "demo/query/read": {
                "inputSchema": {
                    "properties": {
                        "path": {"type": "integer"},
                    },
                },
            },
        },
    }

    problems = lint_handler_signatures(contracts, bindings_doc)

    assert any("demo/query/read.path" in problem for problem in problems)
    assert any("limit" in problem and "no such param" in problem for problem in problems)


def test_callspec_fields_derives_reversibility_from_contract():
    fields = callspec_fields(
        "fs://host/file/command/delete",
        Contract(effect="command", reversible=True, inverse_route="fs://host/file/command/write"),
    )

    assert fields["uri"] == "fs://host/file/command/delete"
    assert fields["mutates"] is True
    assert fields["reversible"] is True
    assert "inverse=fs://host/file/command/write" in fields["note"]
