# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Convert the contract schema-subset dialect to standard JSON Schema."""
from __future__ import annotations

from typing import Any

_LEAF = {
    "str": "string",
    "int": "integer",
    "num": "number",
    "bool": "boolean",
    "obj": "object",
    "list": "array",
}


def _const_value(token: str) -> Any:
    if token == "true":
        return True
    if token == "false":
        return False
    if token.lstrip("-").isdigit():
        return int(token)
    return token


def _dict_schema(dialect: dict) -> dict:
    props: dict[str, Any] = {}
    required: list[str] = []
    for key, spec in dialect.items():
        optional = isinstance(spec, str) and spec.startswith("?")
        props[key] = to_json_schema(spec[1:] if optional else spec)
        if not optional:
            required.append(key)
    schema: dict[str, Any] = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return schema


def _token_schema(tok: str) -> dict:
    if tok.startswith("const:"):
        return {"const": _const_value(tok[len("const:"):])}
    if tok.startswith("enum:"):
        return {"enum": tok[len("enum:"):].split("|")}
    if tok in _LEAF:
        return {"type": _LEAF[tok]}
    return {}


def to_json_schema(dialect: Any) -> dict:
    """Map one contract dialect node to a JSON Schema node."""
    if isinstance(dialect, dict):
        if "oneOf" in dialect:
            return {"oneOf": [to_json_schema(alt) for alt in dialect["oneOf"]]}
        return _dict_schema(dialect)
    if isinstance(dialect, list):
        return {"type": "array", "items": to_json_schema(dialect[0])} if dialect else {"type": "array"}
    tok = dialect[1:] if isinstance(dialect, str) and dialect.startswith("?") else dialect
    return _token_schema(tok) if isinstance(tok, str) else {}
