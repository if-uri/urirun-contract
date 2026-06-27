# ifURI — warstwa kontraktowa: architektura systemu

> Stan na 2026-06-27. Autorytatywne źródło prawdy o kształcie I/O to `contracts.json`
> danego projektu; ten dokument opisuje mechanizm wokół niego.

## Problem i teza

Kształt wyjścia, efekt, odwracalność i taksonomia błędów były emergentne z kodu — wplątane w N
implementacji, dryfowały pod LLM. **Teza**: uczynić kontrakt deklarowanym, wersjonowanym artefaktem
— walidowalnym wobec dowolnej implementacji w dowolnym języku.

**Linia kernela:**

| Nad linią — LLM edytuje | Pod linią — kernel, nie przepisywany |
|---|---|
| `contracts.json` (kształt, efekt, odwracalność, błędy, przykłady) | `gate` (walidator + enforce + kompozycja) |
| ciała handlerów | `codegen` (kontrakt → szkielet) |
| README (intencja) | `lint`, `regen-check`, `conform` (bramy) |

## Jedyne źródła (niezmiennik)

| Komponent | Jedyne źródło | Wszędzie indziej |
|---|---|---|
| gate | `urirun_contract/gate.py` | `from urirun_contract.gate import *` |
| codegen | `urirun_contract/codegen.py` | `from urirun_contract.codegen import ...` |
| toolkit bundled copy | `urirun_connectors_toolkit/contract_gate.py` | synchronizowany z gate.py przy każdej zmianie |

Brama: `check_single_source.py` (FAIL jeśli >1 definicja `consumer_input_check`/`py_stub`).
CI weryfikuje to przy każdym push.

## Artefakt kontraktu

`contracts.json` (neutralny, językowo-agnostyczny) deklaruje:
- **Contract**: `version`, `effect` (`query`/`command`), `reversible`+`inverseRoute`, `inp`/`out`, `errors`, `examples`
- **Wire**: krawędź kompozycji (producer→consumer + mapowanie pól)
- **Mini-język schematu**: `str/int/bool/obj/list/any`, `?x` = opcjonalny, `const:x`, `enum:a|b`, `["int"]` = lista, `{"oneOf":[A,B]}`

Złote `examples` robią podwójną robotę: fixtures konformansu + few-shot dla plannera/MCP.

## Mapa komponentów

| Moduł | Rola |
|---|---|
| `contract_gate` / `gate` | `check`, `enforce`, `conform`, `check_wire`, `wire_payload`, `consumer_input_check` |
| `codegen` | `py_stub`/`js_stub`/`go_stub`, `emit_py_module` |
| `contract_lint` | `lint_handler_signatures` — handler bez kontraktu / sygnatura ≠ generowana |
| `contract_reversible` | `callspecs_from_contracts` — odwracalność z kontraktów dla silnika Twin |
| `contract_jsonschema` | `to_json_schema` — eksport do standardowego JSON Schema |
| `nl_to_contract` (ci) | README → LLM → `contracts.json`, bramkowane przez `validate_doc` |
| `attach_contracts` | Wzbogaca `bindings()` o `outputSchema`/`examples`/`effect`/`errors` |

## Punkty egzekucji

| Punkt | Co sprawdza | Kiedy |
|---|---|---|
| `conform` | efekt↔czasownik URI, wzajemny inverse, przykłady, args-inverse | pre-commit + CI |
| `lint_handler_signatures` | sygnatura/koperta = to, co wygenerowałby codegen | pre-commit + CI |
| `regen-check` | `handlers_generated.py` == świeża generacja | pre-commit + CI |
| `check_single_source.py` | jedyne definicje gate/codegen | CI |
| `enforce` (runtime) | wyjście handlera zgodne z `out` | dev/CI (URIRUN_CONTRACT_CHECK=1) |
| `check` na granicy serwisu | producent waliduje out, konsument waliduje inp | runtime |
| `consumer_input_check` | cross-process: typy, pełny vs częściowy handoff | CI |

**Niezmiennik: kontrakt bez egzekucji w domyślnym torze CI to zielony shim, który kłamie.**

## Format projektu `urirun-contract-*`

```
urirun-contract-<nazwa>/
  README.md                 intencja (źródło dla LLM)
  contracts.json            kształt (źródło prawdy)
  packages/producer/        enforce wyjścia na granicy HTTP
  packages/consumer/        enforce wejścia na granicy HTTP
  packages/consumer-go/     ten sam kontrakt, implementacja Go
  orchestrator/             woła producenta → wire → konsumenta → waliduje
  src/handlers_generated.py GENEROWANE (regen-check pilnuje)
  ci/                       nl_to_contract, emit_handlers, regen_check, pre_commit.sh
  toolkit/                  contract_gate.py (re-eksport), contracts_io.py (loader)
  docker-compose.yml        producent + konsument(y) + orchestrator (exit code = CI)
```

## Polyglot

Gate (~80–250 linii) jest portowalny 1:1 — mini-schemat mapuje się na typy JSON.
Peery: Python + Go (`service.go`). Złote `examples` = językowo-neutralny korpus testowy.

Tarcia per język:
- Go: zero-values → waliduj `map[string]any`, nie struct; liczby jako `float64` → int = sprawdź całkowitość

## Znane problemy (do naprawy)

1. `urirun_connectors_toolkit/contract_gate.py` — bundled copy (437L), zsynchronizowany
   dziś z gate.py. Wymaga ręcznej synchronizacji przy zmianach; docelowo re-eksport gdy
   `urirun-contract` trafi na PyPI i stanie się zależnością toolkit.

2. `TODO/` usunięty — były to stare szablony z nieaktualnym API.

3. `contracts.json` przy korzeniu `urirun-contract` usunięty — kanoniczny egzemplarz
   w `examples/windowpair/contracts.json`.

## Roadmap

- Wpiąć `adapters/conformance.py` jako driver bijący w żywy węzeł (Py/Go) — łapie węzeł
  zgodny u siebie, a kłamiący na drucie
- Opublikować `urirun-contract` na PyPI → re-eksport toolkit bez `@git+...` w Dockerfile
- `contract_jsonschema` → publikować JSON Schema obok kontraktu (walidacja w edytorze)
- Wersjonowanie additive-only per trasa (lub proto `to_proto`)
