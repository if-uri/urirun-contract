#!/usr/bin/env python3
# Part of the ifURI solution — generator deterministyczny (kontrakt → szkielet, polyglot).
"""Czyta contracts.json i emituje moduł szkieletów handlerów w wybranym języku.
Importuje codegen z urirun_contract (jedyne źródło — nie przepisuj tu py_stub/js_stub/go_stub).

  python ci/emit_handlers.py                              # py → src/handlers_generated.py
  python ci/emit_handlers.py --lang js                    # js → src/handlers_generated.mjs
  python ci/emit_handlers.py --lang go contracts.json     # go → src/handlers_generated.go
  python ci/emit_handlers.py --lang go contracts.json -   # stdout

Ten sam contracts.json → szkielet w Pythonie, JS i Go: urirun jako SDK w wielu językach.
Wymaga: pip install urirun-contract
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from urirun_contract.codegen import (  # noqa: E402
    _load_contracts_json, emit_go_module, emit_js_module, emit_py_module,
)

_LANGS = {
    "py": (emit_py_module, "src/handlers_generated.py"),
    "js": (emit_js_module, "src/handlers_generated.mjs"),
    "go": (emit_go_module, "src/handlers_generated.go"),
}


def emit(contracts_path: str, lang: str = "py") -> str:
    emitter, _ = _LANGS[lang]
    return emitter(_load_contracts_json(contracts_path))


def _parse(argv: list[str]) -> tuple[str, str, str]:
    lang = "py"
    if argv and argv[0] == "--lang":
        lang = argv[1]
        argv = argv[2:]
    if lang not in _LANGS:
        raise SystemExit(f"nieznany język {lang!r}; wybierz z {sorted(_LANGS)}")
    contracts_path = argv[0] if argv else os.path.join(ROOT, "contracts.json")
    out_path = argv[1] if len(argv) > 1 else os.path.join(ROOT, _LANGS[lang][1])
    return lang, contracts_path, out_path


if __name__ == "__main__":
    lang, contracts_path, out_path = _parse(sys.argv[1:])
    code = emit(contracts_path, lang)
    if out_path == "-":
        sys.stdout.write(code)
    else:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        open(out_path, "w").write(code)
        print(f"napisano {out_path} ({code.count(chr(10))} linii, {lang})")
