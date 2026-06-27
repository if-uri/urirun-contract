#!/usr/bin/env python3
# Part of the ifURI solution — generator deterministyczny (kontrakt → JSON Schema).
"""Czyta contracts.json i emituje standardowe dokumenty JSON Schema (per trasa: input + output).

Importuje mapper z urirun_contract (jedyne źródło — nie przepisuj tu to_json_schema).
Wynik to zwykłe pliki `*.schema.json` (draft 2020-12) — waliduje payloady w dowolnym
edytorze/jezyku (VS Code, ajv, jsonschema, gojsonschema), bez znajomości dialektu kontraktu.

  python ci/emit_jsonschema.py                              # examples/windowpair/contracts.json → schema/
  python ci/emit_jsonschema.py path/to/contracts.json out/  # inny plik / katalog
  python ci/emit_jsonschema.py contracts.json -             # jeden dokument-index na stdout

Wymaga: pip install urirun-contract
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from urirun_contract.contract_jsonschema import to_json_schema_document  # noqa: E402

_DEFAULT_CONTRACTS = os.path.join(ROOT, "examples", "windowpair", "contracts.json")
_KINDS = (("input", "inp"), ("output", "out"))


def build(contracts_path: str) -> dict[str, dict]:
    """{nazwa_pliku: dokument} dla wszystkich tras (input + output)."""
    doc = json.load(open(contracts_path))
    out: dict[str, dict] = {}
    for route, c in doc.get("contracts", {}).items():
        slug = route.replace("/", ".")
        version = c.get("version", "v1")
        for kind, key in _KINDS:
            schema = to_json_schema_document(route, c.get(key, {}), kind=kind, version=version)
            out[f"{slug}.{kind}.schema.json"] = schema
    return out


def main(argv: list[str]) -> int:
    contracts_path = argv[0] if argv else _DEFAULT_CONTRACTS
    # domyślnie OBOK kontraktu: <katalog contracts.json>/schema
    outdir = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(contracts_path), "schema")
    schemas = build(contracts_path)

    if outdir == "-":  # index: wszystko w jednym dokumencie po $id
        index = {s["$id"]: s for s in schemas.values()}
        json.dump(index, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    os.makedirs(outdir, exist_ok=True)
    for name, schema in sorted(schemas.items()):
        path = os.path.join(outdir, name)
        open(path, "w").write(json.dumps(schema, indent=2, ensure_ascii=False) + "\n")
        print(f"napisano {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
