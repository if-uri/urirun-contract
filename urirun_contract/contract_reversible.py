# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Derive reversible-engine CallSpec data from route contracts."""
from __future__ import annotations

from typing import Any


def callspec_fields(route: str, contract: Any, *, conn_uri=None) -> dict:
    """Return the fields needed by ``urirun_twin.reversible.CallSpec``."""
    effect = getattr(contract, "effect", None) or (contract.get("effect") if isinstance(contract, dict) else "")
    reversible = getattr(contract, "reversible", None)
    if reversible is None and isinstance(contract, dict):
        reversible = contract.get("reversible", False)
    inverse = getattr(contract, "inverse_route", "") or (
        contract.get("inverseRoute") if isinstance(contract, dict) else ""
    )
    uri = route if "://" in route else (conn_uri(route) if conn_uri else route)
    return {
        "uri": uri,
        "mutates": effect == "command",
        "reversible": bool(reversible),
        "note": f"from contract; inverse={inverse}" if reversible else "from contract",
    }


def callspecs_from_contracts(contracts: dict, *, conn_uri=None) -> list:
    """Build ``CallSpec`` objects from contracts.

    The import is lazy so the standalone contract package does not hard-depend on the twin package.
    """
    from urirun_twin.reversible import CallSpec

    return [CallSpec(**callspec_fields(route, contract, conn_uri=conn_uri)) for route, contract in contracts.items()]


def callspecs_from_bindings(bindings: dict, *, conn_uri=None) -> list:
    """Build ``CallSpec`` objects from a COMPILED registry's bindings.

    ``attach_contracts`` joins each route's contract onto its binding under ``meta.contract``
    (carrying ``effect``/``reversible``/``inverseRoute``), so the compiled registry already holds
    the reversibility truth. This is the registry→engine-schema bridge: any holder of the registry
    (host flow execution, a connector's ``schema()``) derives the reversibility schema from the
    contract — the single source — instead of a hand-maintained parallel table. Bindings without a
    ``meta.contract`` are skipped (no contract = unknown, left to the fail-safe default)."""
    from urirun_twin.reversible import CallSpec

    specs = []
    for uri, binding in (bindings or {}).items():
        contract = ((binding or {}).get("meta") or {}).get("contract")
        if isinstance(contract, dict):
            specs.append(CallSpec(**callspec_fields(uri, contract, conn_uri=conn_uri)))
    return specs
