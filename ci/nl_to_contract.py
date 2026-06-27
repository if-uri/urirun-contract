#!/usr/bin/env python3
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""README (NL) → contracts.json przez lokalny LLM (LiteLLM), z BRAMĄ konformansu.

Cokolwiek model zwróci, musi przejść bramy (efekt↔czasownik, wzajemny inverse, przykłady
spełniają in/out) — halucynowany kontrakt jest ODRZUCONY. Człowiek recenzuje wynik w PR.

  (domyślnie)         README.md → LLM → walidacja → contracts.json
  --mock              zwróć poprawny kanoniczny kontrakt (offline; do CI/demo)
  --mock-bad          zwróć kontrakt z NIEwzajemnym inverse (pokazuje, że brama odrzuca)
  --validate <plik>   tylko zwaliduj istniejący contracts.json (bez LLM) — używane w pre-commit
"""
from __future__ import annotations

import json
import os
import sys

from urirun_contract.gate import check

SCHEMA_HINT = """Zwróć WYŁĄCZNIE JSON: {"schemaVersion":1,"contracts":{<route>:{
"version","effect"(query|command),"reversible","inverseRoute","inp","out","errors","examples"}},"wires":[...]}.
Tokeny schematu: str/int/bool/obj/list, "?x" opcjonalne, "const:x", "enum:a|b", {"oneOf":[...]}.
Efekt MUSI zgadzać się z czasownikiem URI (/query/ ⇒ query). reversible ⇒ inverseRoute wzajemny.
Każdy przykład {payload,result} musi spełniać inp/out."""


def ask_llm(readme: str, model: str = "") -> dict:
    import litellm
    cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "litellm.config.yaml")
    model = model or os.environ.get("LITELLM_MODEL", "ollama/llama3.1")
    resp = litellm.completion(
        model=model,
        messages=[{"role": "system", "content": SCHEMA_HINT},
                  {"role": "user", "content": f"README projektu:\n\n{readme}"}],
        config_path=cfg if os.path.exists(cfg) else None,
        temperature=0)
    text = resp["choices"][0]["message"]["content"]
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


def validate_doc(doc: dict) -> list[str]:
    """Brama: ta sama logika co conform() ale na surowym JSON-ie z LLM."""
    C = doc.get("contracts", {})
    problems: list[str] = []
    for route, c in C.items():
        if ("/query/" in route) != (c.get("effect") == "query"):
            problems.append(f"{route}: efekt {c.get('effect')!r} nie zgadza się z czasownikiem URI")
        if c.get("reversible"):
            inv = c.get("inverseRoute")
            if inv not in C:
                problems.append(f"{route}: inverseRoute {inv!r} nie istnieje")
            elif C[inv].get("inverseRoute") != route:
                problems.append(f"{route} ⟂ {inv} nie jest wzajemne")
        for i, ex in enumerate(c.get("examples", [])):
            try:
                check(c.get("inp", {}), ex.get("payload", {}), f"{route}#ex{i}.payload")
            except AssertionError as exc:
                problems.append(str(exc))
            if ex.get("result", {}).get("ok"):
                try:
                    check(c.get("out", {}), ex["result"], f"{route}#ex{i}.result")
                except AssertionError as exc:
                    problems.append(str(exc))
    return problems


def _mock(bad: bool, contracts_path: str) -> dict:
    doc = json.load(open(contracts_path))
    if bad:  # zepsuj wzajemność — brama MUSI to złapać
        first_route = next(iter(doc["contracts"]))
        inv = doc["contracts"][first_route].get("inverseRoute", "")
        if inv:
            doc["contracts"][inv]["inverseRoute"] = inv + "X"
    return doc


def main() -> int:
    args = sys.argv[1:]
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    contracts_path = os.path.join(root, "contracts.json")

    if args and args[0] == "--validate":
        path = args[1] if len(args) > 1 else contracts_path
        doc = json.load(open(path))
    elif "--mock" in args or "--mock-bad" in args:
        doc = _mock(bad="--mock-bad" in args, contracts_path=contracts_path)
    else:
        readme_path = os.path.join(root, "README.md")
        if not os.path.exists(readme_path):
            print("BŁĄD: brak README.md — opisz intencję kontraktu", file=sys.stderr)
            return 1
        doc = ask_llm(open(readme_path).read())

    problems = validate_doc(doc)
    if problems:
        print("ODRZUCONO kontrakt (brama konformansu):", file=sys.stderr)
        for p in problems:
            print(f"  FAIL {p}", file=sys.stderr)
        return 1

    if args and args[0] == "--validate":
        print(f"OK: {args[1] if len(args) > 1 else contracts_path} konformuje "
              f"({len(doc['contracts'])} kontraktów)")
    else:
        json.dump(doc, open(contracts_path, "w"), indent=2, ensure_ascii=False)
        print(f"OK: napisano contracts.json ({len(doc['contracts'])} kontraktów) — zrecenzuj w PR")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
