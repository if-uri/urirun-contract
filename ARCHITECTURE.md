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
| JSON Schema | `urirun_contract/contract_jsonschema.py` | re-eksport |
| lint | `urirun_contract/contract_lint.py` | re-eksport |
| reversible | `urirun_contract/contract_reversible.py` | re-eksport |
| compat | `urirun_contract/contract_compat.py` | re-eksport |
| scaffold | `urirun_contract/contract_scaffold.py` | re-eksport |
| export | `urirun_contract/contract_export.py` | re-eksport |
| TypeScript | `urirun_contract/contract_typescript.py` | re-eksport |

Brama: `check_single_source.py` (FAIL jeśli >1 definicja kernela, np. `consumer_input_check`,
`py_stub`, `to_json_schema`, `lint_handler_signatures`, `callspecs_from_contracts`, `incompatibilities`,
`contracts_from_manifest`, `neutral_document`, `to_typescript`). CI weryfikuje to przy każdym push.

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
| `contract_lint` | `lint_handler_signatures` — handler bez kontraktu / sygnatura != generowana |
| `contract_reversible` | `callspecs_from_contracts` → most `urirun_twin.reversible.schema_from_contracts`: kontrakt jako schemat odwracalności silnika (strategia #3, `Connector.schema()` zwraca to zamiast ręcznych CallSpec). **Runtime ledger nadal jedzie konwencją „inverse w wyniku" (#2)**; most udowodniony end-to-end (`test_reversible.py::test_contract_derived_schema_drives_the_engine_invariant`) |
| `contract_jsonschema` | `to_json_schema` — eksport do standardowego JSON Schema |
| `contract_export` | `neutral_document`/`schema_document`/`write_artifacts` — neutralny JSON + JSON Schema + TS |
| `contract_typescript` | `to_typescript` — mini-schemat kontraktu → typy TypeScript |
| `contract_compat` | `compare_route`/`incompatibilities` — additive-only per trasa (wariancja inp/out) |
| `nl_to_contract` (ci) | README → LLM → `contracts.json`, bramkowane przez `validate_doc` |
| `attach_contracts` | Wzbogaca `bindings()` o `outputSchema`/`examples`/`effect`/`errors` |

## Punkty egzekucji

| Punkt | Co sprawdza | Kiedy |
|---|---|---|
| `conform` | efekt↔czasownik URI, wzajemny inverse, przykłady, args-inverse | pre-commit + CI |
| `lint_handler_signatures` | sygnatura/koperta = to, co wygenerowałby codegen | pre-commit + CI |
| `regen-check` | `handlers_generated.py` == świeża generacja | pre-commit + CI |
| `check_single_source.py` | jedyne definicje kernela (gate/codegen/jsonschema/lint/reversible/compat) | pytest + CI |
| `test_no_kernel_drift` | shim toolkit re-eksportuje DOKŁADNIE `__all__`, te same obiekty (`is`) | pytest + CI |
| `check_compat.py` | zmiana trasy przy tej samej wersji wstecznie kompatybilna (vs baseline) | pre-commit + CI |
| `fleet_coverage.py --baseline` | ratchet floty: brak nowych mutujących connectorów bez kontraktu | pre-commit + CI |
| `enforce` (runtime) | wyjście handlera zgodne z `out` | dev/CI (URIRUN_CONTRACT_CHECK=1) |
| `check` na granicy serwisu | producent waliduje out, konsument waliduje inp | runtime |
| `consumer_input_check` | cross-process: typy, pełny vs częściowy handoff | CI |

**Niezmiennik: kontrakt bez egzekucji w domyślnym torze CI to zielony shim, który kłamie.**

### Adopcja floty (`contract_scaffold` + `fleet_coverage`)

~37 konektorów, kontrakt ma 14 (i rośnie) — reszta to dryf ×N. Adopcja **generacją, nie ręką**:
`contract_scaffold.contracts_from_manifest`/`contracts_from_routes` buduje szkielet `contracts.json`
z tras connectora. Trasy odkrywane z TRZECH źródeł: `discover_routes` (dekoratory `@conn.handler/
command/query` w `core.py` — źródło prawdy connectorów Python) + `connector.manifest.json` +
`contracts_from_bindings`/`routes_from_bindings` (runtime `urirun_bindings()` przez entry-point
`urirun.bindings` — dla connectorów budujących bindings PROGRAMOWO/deklaratywnie, bez dekoratorów;
np. `ksef` ma 0 dekoratorów, ale `urirun_bindings()` zwraca ~39 tras). Efekt z czasownika trasy,
wejście wywnioskowane z przykładów; `out`/`reversible`/`errors` zostają puste — `scaffold_gaps`
mówi, co człowiek/LLM ma dopisać. Szkielet KONFORMUJE od razu (poprawny punkt startowy, nie śmieć).
`ci/fleet_coverage.py` raportuje pokrycie i NAZYWA konektory z trasą mutującą (`/command/`) bez
kontraktu. Domyślny tor używa `ci/fleet_coverage.baseline.json` jako ratchetu: obecne braki są
jawne, ale nowy mutujący connector bez kontraktu failuje pre-commit/CI. `--strict` failuje na
wszystkie braki i jest celem po domknięciu adopcji. Konektor bez wykrywalnych tras jest raportowany
JAWNIE jako „nieznany", nie cicho przepuszczany. `make scaffold CONN=...` / `make fleet-coverage`.

**Wzorzec uzupełniania (od szkieletu do kontraktu).** Szkielet daje trasy + efekt + wejście; `out`
trzeba dopisać WIERNIE wobec `core.py`, nie zgadując. Większość connectorów zwraca przez
`urirun.ok(**fields)` = `{ok:True, **fields}`, więc kształt `out` = jawne kwargi (`const:` dla
literałów typu `action`, stałe pola + `**meta`/`**bindings` jako nadmiar dozwolony). Pola rozbieżne
między gałęziami → `?opcjonalne` albo `{"oneOf":[…]}`. Każdy adoptowany connector dostaje
`tests/test_contract.py`: `conform` (efekt↔czasownik, przykłady spełniają in/out, reguły reversible)
+ „każda trasa `@conn.handler` (po `route_key`) ma wpis w `contracts.json`" — to anti-dryf deklaracja↔kod.
Connectory mutujące-odwracalne deklarują `reversible:true` + `inverseRoute` (np. `namecheap-dns`
`records/command/apply` wymusza `backup_uri` do rollbacku → inverse = ponowny apply backupu).
Zaadoptowane jako wzorzec: `sheet`, `llm`, `github`, `webcam`, `mqtt`, `namecheap-dns`.

> **Caveat konwencji URI (ksef):** odkrycie tras nie wystarcza, gdy URI łamią kształt
> `noun/verb/action`. Trasy ksef (`ksef://{env}/auth/challenge`, `cert/enroll`,
> `session/online/{ref}/send` — czasownik na końcu, bez `/command/`//`/query/`) nie pozwalają
> wywnioskować efektu z czasownika, a `conform` (efekt↔czasownik) je odrzuci. ksef wymaga decyzji:
> remap URI na konwencję albo rozszerzenie inferencji efektu o kształt „verb-na-końcu". `scanner`
> jest poprawnie „nieznany" — to serwis/most (`urirun.services`), nie connector z bindings.

### Wersjonowanie additive-only (`contract_compat`)

Zmiana kontraktu trasy przy TEJ SAMEJ wersji musi być wstecznie kompatybilna; zmiana łamiąca
wymaga bumpa `version` (v1→v2) albo świadomego przemrożenia baseline (`make freeze`). Sednem jest
**wariancja**: `out` kowariantne (obietnica producenta — wolno dodać pole / wzmocnić `?T`→`T`, nie
wolno usunąć / osłabić `T`→`?T`), `inp` kontrawariantne (obowiązek wołającego — wolno dodać
opcjonalne / zluzować `T`→`?T` / usunąć wymóg, nie wolno dodać wymagane / zacieśnić `?T`→`T`).
Brama `check_compat.py` porównuje `contracts.json` z zamrożonym `contracts.baseline.json`; głębokie
zmiany struktury (oneOf/enum) traktowane konserwatywnie (różne = łamiące). `make compat` / `make freeze`.

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

### SDK runtime (`sdk/`)

`sdk/js/contract.mjs` i `sdk/go/contract/` to reużywalne guardy koperty — port 1:1 kernela
(`check` + `envelopeViolation`). Connector w JS/Go woła `envelopeViolation(contract, env)` przed
zwróceniem koperty: kształt rozjechany z kontraktem → komunikat zamiast cichego dryfu. Każdy ma
CLI parytetu (`node contract.mjs <json> <route>` / `go run ./cmd/enforce <json> <route>`, koperta
ze stdin → `OK`/`VIOLATION`). `make enforce-xlang` dowodzi: ta sama złota koperta przechodzi w
Py/JS/Go, ten sam fixture dryfu (bool→string łamie `const:true`) jest łapany wszędzie.

**Generator spięty z SDK** (`emit_handlers.py --enforce <import>`, `make gen-js SDK=...`): wygenerowany
moduł JS importuje `check` z SDK, wpieka schematy `out` i `ok(route, fields)` waliduje kopertę PRZED
zwrotem (zła koperta rzuca). Go emituje pomocnik `Guard(route, env)` (importuje `contract.Check`).
Domyka pętlę generuj→samo-pilnuj: connector w JS/Go nie może po cichu zwrócić koperty niezgodnej
z kontraktem. JS dowiedziony runtime, Go kompilacją z SDK (`tests/test_codegen_enforce.py`).

## Driver konformancji (zewnętrzny, po drucie)

`conform` (gate.py) waliduje kontrakt i złoty korpus *w jednym procesie* — to konformancja
**u siebie**. Węzeł może ją przejść, a mimo to **kłamać na drucie**: zserializować int/bool
jako string, zgubić pole, zwrócić nieobjętą taksonomią klasę błędu. `adapters/conformance.py`
to łapie, bo czyta to, co realnie wyszło z gniazda HTTP — nie obiekt Pythona.

Dla każdej trasy ze złotym przykładem ok: bierze `payload`, POST do żywego węzła, wyciąga
kopertę z odpowiedzi, woła `envelope_violation(contract, envelope)`. Exit code = liczba
naruszeń. Profile transportu: `peer` (generyczny `xlang/peer.py serve-http`, steruje wszystkie
trasy) i `direct` (usługa pod jedną trasę, np. Go `consumer-go`). `make conformance` / fikstura
`xlang/peer.py serve-http --lie` dowodzą obu kierunków (zgodny → 0, kłamiący → ≥1).

## Znane problemy (do naprawy)

1. `urirun_connectors_toolkit/contract_gate.py` (i kopie `toolkit/` w projektach `urirun-contract-*`)
   to shimy re-eksportujące CAŁY pakiet: `from urirun_contract import *` (nie `.gate` — kernel rozlał
   się na gate/jsonschema/lint/reversible, więc import z `.gate` gubił `to_json_schema`/`lint`/`callspecs`).
   Nie wolno przywracać lokalnej kopii kernela ani importu z `.gate`; pilnują tego `check_single_source.py`
   (jedna definicja) + `test_no_kernel_drift` (shim == `__all__`, te same obiekty).

2. `TODO/` usunięty — były to stare szablony z nieaktualnym API.

3. `contracts.json` przy korzeniu `urirun-contract` usunięty — kanoniczny egzemplarz
   w `examples/windowpair/contracts.json`.

4. **Odwracalność: most jest, produkcja jeszcze nie.** `schema_from_contracts` (strategia #3)
   jest błogosławiony i udowodniony testem (`test_reversible.py`), ale ŻADEN produkcyjny
   `Connector.schema()` go nie woła, a twin planner (`urirun-connector-twin`,
   `urirun_connector_twin/planner.py`) nadal wyznacza odwracalność z ręcznej tablicy
   `_REVERSIBLE_TABLE` — równoległa deklaracja, której niezmiennik #3 zabrania. Domknięcie wymaga
   rejestru kontraktów niosącego `reversible`/`inverseRoute` (dziś `attach_contracts` wystawia
   `effect`/`errors`/`outputSchema`, nie odwracalność), z którego planner i konektory czytałyby
   zamiast tablicy. Runtime ledger nadal poprawnie jedzie konwencją „inverse w wyniku" (#2).

5. **Bramy egzekucji żyją w `urirun-contract`, nie w monorepo `urirun`.** `check_single_source` /
   regen-check / `lint_handler_signatures` siedzą w `make check` + CI + pre-commit TEGO repo. W
   monorepo `urirun` nie ma `make check` ani flota-lintu na trasy mutujące bez `contracts.py` —
   konektory tam (kvm itd.) nie są bramkowane. (Pokrycie floty jest ratchetowane osobno:
   `fleet_coverage.py`, 8/37 z kontraktem.)

## Roadmap

- ✅ `adapters/conformance.py` — driver bijący w żywy węzeł (Py/Go) łapie węzeł zgodny
  u siebie, a kłamiący na drucie (`make conformance`, testy `tests/test_conformance.py`)
- ✅ Anty-drift kernela — shim toolkit == `__all__` (te same obiekty), `check_single_source`
  w torze pytest (`tests/test_no_kernel_drift.py`)
- ✅ JSON Schema obok kontraktu — `ci/emit_jsonschema.py` → `<contract>/schema/*.schema.json`
  (draft 2020-12, `make schema`); golden corpus waliduje jako wektor testowy
  (`tests/test_jsonschema_emit.py`)
- ✅ Polyglot SDK — `emit_js_module`/`emit_go_module` + `ci/emit_handlers.py --lang py|js|go`
  (`make gen-js`/`gen-go`); JS przechodzi `node --check`, Go kompiluje się i jest gofmt-clean
  (`tests/test_polyglot_emit.py`)
- ✅ Projekcje neutral/JSON Schema/TypeScript w jednym źródle — `contract_export` i
  `contract_typescript` żyją w `urirun_contract`; `urirun_connectors_toolkit` jest facade
  (`tests/test_contract_export.py`, `check_single_source`)
- ✅ Runtime `enforce` per język (JS/Go) — reużywalny guard koperty `sdk/js` + `sdk/go`,
  parytet z kernelem na złotym korpusie + fixture dryfu (`make enforce-xlang`,
  `tests/test_runtime_enforce_xlang.py`)
- ✅ Generowane szkielety JS/Go spięte z SDK (`--enforce`) — moduł sam waliduje kopertę
  (`tests/test_codegen_enforce.py`)
- ✅ Wersjonowanie additive-only per trasa — `contract_compat` (wariancja inp/out) + brama
  `check_compat.py` vs baseline (`make compat`/`freeze`, `tests/test_compat.py`)
- ✅ Pokrycie floty jako ratchet — `fleet_coverage.py --baseline` w pre-commit/CI; stan jawny:
  8/37 connectorów z kontraktem, 13 znanych mutujących bez kontraktu, 2 nieznane
  (`tests/test_fleet_coverage.py`)
- Opublikować `urirun-contract` na PyPI (+ `sdk/go` jako publikowalny moduł, `sdk/js` jako pakiet npm)
  → re-eksport toolkit bez `@git+...`, `--enforce` z bare-specifier zamiast ścieżki
- Eksport `to_proto`/protobuf obok JSON Schema (binarne kontrakty cross-lang)
