# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Generic contract exporter.

From one connector ``CONTRACTS`` map this module emits neutral JSON, JSON Schema and TypeScript
artifacts for polyglot consumers. It is intentionally pure and connector-agnostic.
"""
from __future__ import annotations

import importlib
import json
import os

from urirun_contract.contract_jsonschema import to_json_schema
from urirun_contract.contract_typescript import to_typescript

SCHEMA_VERSION = 1


def neutral_document(contracts: dict, wires=()) -> dict:
    """Build polyglot ``contracts.json`` from ``{route: Contract}`` plus optional wires."""
    return {
        "schemaVersion": SCHEMA_VERSION,
        "source": "connector CONTRACTS (dataclass) - GENERATED, do not hand-edit",
        "contracts": {
            route: {
                "version": c.version,
                "effect": c.effect,
                "reversible": c.reversible,
                "inverseRoute": (c.inverse_route or None),
                "inp": c.inp,
                "out": c.out,
                "errors": list(c.errors),
                "examples": [dict(ex) for ex in c.examples],
            }
            for route, c in contracts.items()
        },
        "wires": [
            {"producer": w.producer, "consumer": w.consumer, "mapping": w.mapping,
             "note": getattr(w, "note", "")}
            for w in wires
        ],
    }


def schema_document(contracts: dict) -> dict:
    """Standard JSON Schema document with per-route ``input``/``output`` schemas."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "route contracts - generated JSON Schema",
        "source": "connector CONTRACTS (dataclass) - GENERATED, do not hand-edit",
        "routes": {
            route: {"input": to_json_schema(c.inp), "output": to_json_schema(c.out)}
            for route, c in contracts.items()
        },
    }


def write_artifacts(contracts: dict, wires=(), out_dir: str = ".") -> list[str]:
    """Write ``contracts.json``, ``contracts.schema.json`` and ``ts/contracts.d.ts``."""
    os.makedirs(os.path.join(out_dir, "ts"), exist_ok=True)
    written = []

    def _dump_json(name, obj):
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        written.append(path)

    _dump_json("contracts.json", neutral_document(contracts, wires))
    _dump_json("contracts.schema.json", schema_document(contracts))
    ts_path = os.path.join(out_dir, "ts", "contracts.d.ts")
    with open(ts_path, "w", encoding="utf-8") as fh:
        fh.write(to_typescript(contracts))
    written.append(ts_path)
    return written


def _load(module_path: str):
    mod = importlib.import_module(module_path)
    return getattr(mod, "CONTRACTS"), getattr(mod, "WIRES", [])


def main(argv=None) -> int:
    import sys
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("usage: python -m urirun_contract.contract_export <module.with.CONTRACTS> [out_dir]",
              file=sys.stderr)
        return 2
    module_path = args[0]
    out_dir = args[1] if len(args) > 1 else "."
    contracts, wires = _load(module_path)
    written = write_artifacts(contracts, wires, out_dir)
    print(f"wrote {len(written)} artifacts from {module_path} "
          f"({len(contracts)} routes, {len(wires)} wires):")
    for p in written:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
