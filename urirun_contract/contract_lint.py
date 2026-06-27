# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Static lint binding handler signatures to their declared contracts."""
from __future__ import annotations

from typing import Any

_TOKEN_JSON_TYPE = {
    "str": "string",
    "int": "integer",
    "num": "number",
    "bool": "boolean",
    "obj": "object",
    "list": "array",
}


def _base(tok: Any) -> str:
    return tok[1:] if isinstance(tok, str) and tok.startswith("?") else (tok if isinstance(tok, str) else "")


def _check_field_type(route: str, field: str, tok: Any, props: dict, problems: list[str]) -> None:
    if field not in props:
        problems.append(f"{route}: contract.inp declares {field!r} but the handler signature has no such param")
        return
    base = _base(tok)
    if not base or base.startswith(("const:", "enum:")):
        return
    want = _TOKEN_JSON_TYPE.get(base)
    got = (props[field] or {}).get("type")
    if want and got and want != got:
        problems.append(f"{route}.{field}: contract type {base!r} (JSON {want!r}) != signature type {got!r}")


def lint_handler_signatures(contracts: dict, bindings_doc: dict, *, conn_uri=None) -> list[str]:
    """Return contract/signature problems. Empty list means clean."""
    bindings = bindings_doc.get("bindings", {})
    problems: list[str] = []
    for route, c in contracts.items():
        inp = getattr(c, "inp", None)
        if inp is None and isinstance(c, dict):
            inp = c.get("inp", {})
        uri = route if "://" in route else (conn_uri(route) if conn_uri else route)
        binding = bindings.get(uri)
        if binding is None:
            problems.append(f"{route}: contract has no live binding (route not served at {uri!r})")
            continue
        props = (binding.get("inputSchema") or {}).get("properties") or {}
        for field, tok in (inp or {}).items():
            _check_field_type(route, field, tok, props, problems)
    return problems
