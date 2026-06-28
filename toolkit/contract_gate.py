# toolkit/contract_gate.py — re-eksport CAŁEGO publicznego API urirun_contract (jedyne źródło definicji).
# Nie edytuj listy ręcznie: test_no_kernel_drift pilnuje, że == urirun_contract.__all__ (te same obiekty).
# Importuj z PAKIETU (nie z .gate) — kernel rozlał się na gate/jsonschema/lint/reversible.
# Zainstaluj: pip install urirun-contract
#   lub: pip install git+https://github.com/if-uri/urirun-contract.git
from urirun_contract import *  # noqa: F401,F403
from urirun_contract import (  # noqa: F401 — explicit dla IDE / type-checkerów (== __all__)
    Contract, ContractViolation, Wire,
    attach_contracts, callspec_fields, callspecs_from_contracts,
    check, check_wire, conform, consumer_input_check, contract_to_dict,
    dig, enforce, envelope_violation, find_wire,
    lint_handler_signatures, neutral_document, resolve_out_type, schema_document,
    to_json_schema, to_typescript, validate_output, wire_payload, write_artifacts,
)
