# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""urirun-contract — standalone contract gate for urirun connectors.

A ``Contract`` makes a route's output shape, effect class, reversibility and error taxonomy
a declared, versioned entity instead of convention. A ``Wire`` declares a composition edge.

Public API::

    from urirun_contract import Contract, Wire, conform, enforce, check, check_wire
"""
from urirun_contract.gate import (
    Contract,
    ContractViolation,
    Wire,
    attach_contracts,
    check,
    check_wire,
    conform,
    consumer_input_check,
    contract_to_dict,
    dig,
    enforce,
    envelope_violation,
    find_wire,
    resolve_out_type,
    validate_output,
    wire_payload,
)

__all__ = [
    "Contract",
    "ContractViolation",
    "Wire",
    "attach_contracts",
    "check",
    "check_wire",
    "conform",
    "consumer_input_check",
    "contract_to_dict",
    "dig",
    "enforce",
    "envelope_violation",
    "find_wire",
    "resolve_out_type",
    "validate_output",
    "wire_payload",
]
