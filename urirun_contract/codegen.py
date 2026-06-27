#!/usr/bin/env python3
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Generator szkieletów handlerów z deklaracji kontraktu.

Domyka pętlę deklaracja→kod: model edytuje DEKLARACJĘ (contracts.json lub contracts.py);
generator DETERMINISTYCZNIE emituje sygnaturę + kształt koperty; człowiek/LLM dopisuje tylko
CIAŁO logiki. Kontrakt nie może zdryfować, bo kształt jest generowany, nie przepisywany.

Może działać z dowolnym źródłem kontraktów (``dict[str, Contract]`` lub SimpleNamespace);
nie wymaga żadnego konkretnego connectora.

CLI::

    python -m urirun_contract.codegen py  screen/query/capture
    python -m urirun_contract.codegen js  window/command/close
    python -m urirun_contract.codegen go  abs/command/click
    python -m urirun_contract.codegen all-py  contracts.json   # all routes from JSON

Albo API::

    from urirun_contract.codegen import py_stub, js_stub, go_stub
    code = py_stub(route, contract)
"""
from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from typing import Any

# token schematu → (typ Pythona, wartość domyślna)
_PY = {"str": ("str", '""'), "int": ("int", "0"), "num": ("float", "0.0"),
       "bool": ("bool", "False"), "obj": ("dict | None", "None"),
       "list": ("list | None", "None"), "any": ("object", "None")}
_JS = {"str": '""', "int": "0", "num": "0", "bool": "false",
       "obj": "null", "list": "null", "any": "null"}
_GO = {"str": '""', "int": "0", "num": "0", "bool": "false",
       "obj": "nil", "list": "nil", "any": "nil"}


def _base(tok: str) -> str:
    return tok[1:] if (isinstance(tok, str) and tok.startswith("?")) else tok


def _snake(route: str) -> str:
    return route.split("/")[-1].replace("-", "_")


def _camel(route: str) -> str:
    last = route.split("/")[-1]
    parts = last.replace("-", "_").split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def _const(tok: str) -> Any:
    lit = tok[len("const:"):]
    return True if lit == "true" else False if lit == "false" else lit


def _inp(c) -> dict:
    return c.inp if isinstance(c.inp, dict) else {}


def _out(c) -> dict:
    return c.out if isinstance(c.out, dict) else {}


def _py_value(schema: Any) -> str:
    if isinstance(schema, dict):
        if set(schema) == {"oneOf"}:
            return "{}  # oneOf: " + " | ".join(
                "{" + ",".join(sorted(b)) + "}" for b in schema["oneOf"])
        inner = ", ".join(f'"{k}": {_py_value(v)}' for k, v in schema.items())
        return "{" + inner + "}"
    if isinstance(schema, list):
        return "[]"
    s = _base(schema)
    if isinstance(s, str) and s.startswith("const:"):
        v = _const(s)
        return repr(v) if isinstance(v, str) else str(v)
    return {"str": '""', "int": "0", "num": "0.0", "bool": "False",
            "obj": "{}", "list": "[]", "any": "None"}.get(s, "None")  # type: ignore[arg-type]


def py_stub(route: str, c) -> str:
    """Generate a Python @conn.handler skeleton for one route."""
    params = []
    for key, tok in _inp(c).items():
        if not isinstance(tok, str):
            continue
        pytype, default = _PY.get(_base(tok), ("object", "None"))
        params.append(f"{key}: {pytype} = {default}")
    sig = ", ".join(params) if params else ""
    out = _out(c)
    if set(out) == {"oneOf"}:
        succ = out["oneOf"][0]
        body_kv = ", ".join(f'{k}={_py_value(v)}' for k, v in succ.items())
        ret = f"return _ok({body_kv})  # oneOf — wariant Degraded zwróć osobną gałęzią"
    else:
        body_kv = ", ".join(f'{k}={_py_value(v)}' for k, v in out.items())
        ret = f"return _ok({body_kv})"
    version = getattr(c, "version", "v1")
    return (f'@conn.handler("{route}", isolated=True, meta={{"label": "TODO: {route}"}})\n'
            f"def {_snake(route)}({sig}) -> dict[str, Any]:\n"
            f'    """WYGENEROWANE Z KONTRAKTU {version}. Sygnatura i kształt koperty pochodzą z\n'
            f'    contracts.json — NIE edytuj ich ręcznie (build odrzuci dryf). Uzupełnij tylko ciało."""\n'
            f'    raise NotImplementedError("ciało {route}")  # noqa: F841 — uzupełnij logikę, potem:\n'
            f"    {ret}")


def js_stub(route: str, c) -> str:
    """Generate a JS handler skeleton."""
    inp = _inp(c)
    dargs = ", ".join(f"{k} = {_JS.get(_base(t), 'null')}" for k, t in inp.items()
                      if isinstance(t, str))
    out = _out(c)
    out_v = out["oneOf"][0] if set(out) == {"oneOf"} else out

    def jsval(v: Any) -> str:
        if isinstance(v, dict):
            return "{" + ", ".join(f"{k}: {jsval(x)}" for k, x in v.items()) + "}"
        if isinstance(v, list):
            return "[]"
        s = _base(v)
        if isinstance(s, str) and s.startswith("const:"):
            cv = _const(s)
            return f'"{cv}"' if isinstance(cv, str) else str(cv).lower()
        return {"str": '""', "int": "0", "bool": "false", "obj": "{}", "list": "[]"}.get(s, "null")  # type: ignore[arg-type]

    body = ", ".join(f"{k}: {jsval(v)}" for k, v in out_v.items())
    version = getattr(c, "version", "v1")
    return (f"// WYGENEROWANE Z KONTRAKTU {version} — kształt z contracts.json, nie edytuj ręcznie\n"
            f"export function {_camel(route)}({{ {dargs} }} = {{}}) {{\n"
            f'  throw new Error("ciało {route}");          // uzupełnij logikę, potem:\n'
            f"  return ok({{ {body} }});\n"
            f"}}")


def go_stub(route: str, c) -> str:
    """Generate a Go handler skeleton."""
    inp = _inp(c)

    def _go_type(tok: Any) -> str:
        b = _base(tok)
        return {"str": "string", "int": "int", "num": "float64", "bool": "bool",
                "obj": "map[string]any", "list": "[]any", "any": "any"}.get(b, "any")  # type: ignore[arg-type]

    fields = "\n".join(f'\t{k.title()} {_go_type(t)} `json:"{k}"`'
                       for k, t in inp.items() if isinstance(t, str))
    version = getattr(c, "version", "v1")
    name = _camel(route).title()
    return (f"// WYGENEROWANE Z KONTRAKTU {version} — kształt z contracts.json, nie edytuj ręcznie\n"
            f"type {name}In struct {{\n{fields}\n}}\n\n"
            f"func {name}(in {name}In) (map[string]any, error) {{\n"
            f'\treturn nil, fmt.Errorf("ciało {route} niezaimplementowane")\n'
            f"\t// po implementacji zwróć kopertę zgodną z out-schematem kontraktu\n"
            f"}}")


def _load_contracts_json(path: str) -> dict:
    """Load contracts.json → dict[route, SimpleNamespace]."""
    doc = json.load(open(path))
    return {route: SimpleNamespace(**{**c, "inverse_route": c.get("inverseRoute") or ""})
            for route, c in doc.get("contracts", {}).items()}


def emit_py_module(contracts: dict, header: str = "") -> str:
    """Generate a complete Python module with handler stubs for all routes."""
    default_header = ("# WYGENEROWANE Z contracts.json — NIE EDYTUJ RĘCZNIE.\n"
                      "# Przegeneruj: `make gen`. Bramą jest ci/regen_check.py.\n"
                      "from typing import Any\n\n"
                      "# from .conn import conn, _ok  # zapewnione przez pakiet connectora\n\n")
    blocks = [py_stub(route, c) for route, c in sorted(contracts.items())]
    return (header or default_header) + "\n\n".join(blocks) + "\n"


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Użycie: python -m urirun_contract.codegen <lang> <route_or_json>")
        print("  lang: py | js | go | all-py")
        raise SystemExit(0)
    lang = args[0]
    if lang == "all-py":
        path = args[1] if len(args) > 1 else "contracts.json"
        contracts = _load_contracts_json(path)
        out = args[2] if len(args) > 2 else "-"
        code = emit_py_module(contracts)
        if out == "-":
            sys.stdout.write(code)
        else:
            open(out, "w").write(code)
            print(f"napisano {out}")
    else:
        if len(args) < 3:
            print("Użycie: python -m urirun_contract.codegen py|js|go <route> <contracts.json>")
            raise SystemExit(1)
        route, path = args[1], args[2]
        contracts = _load_contracts_json(path)
        c = contracts[route]
        print({"py": py_stub, "js": js_stub, "go": go_stub}[lang](route, c))
