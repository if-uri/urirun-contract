# urirun-contract

**Deklaratywne kontrakty tras dla connectorów urirun.**

Kształt wyjścia, klasa efektu (query/command), odwracalność i taksonomia błędów są dziś
tylko *konwencją* — emergentną z rozproszonych `return`. LLM edytujący handler nie ma punktu
zakotwiczenia i dryfuje. Ten pakiet czyni kontrakt **deklarowaną, wersjonowaną encją**.

```
README.md ──(lokalny LLM)──▶ contracts.json ──(generator det.)──▶ src/handlers_generated.py
   intencja      proponuje,              kształt prawdy         sygnatura + koperta (nie edytuj)
                 człowiek recenzuje                                     │
                 + commituje                                            ▼ człowiek/LLM pisze CIAŁO
                                                                 src/handlers.py
                                                                        │
                                                                        ▼ enforce + conform (det.)
                                                                 registry (bindings.v2)
```

LLM biegnie **lokalnie** (LiteLLM + ollama / llama.cpp / vLLM). Do CI nie dociera — CI weryfikuje
deterministycznie: kontrakt i wygenerowany kod są już w repo, brama tylko sprawdza zgodność.

## Instalacja

```bash
pip install urirun-contract
```

## Użycie w connectorze

```python
# contracts.py — jedyne źródło prawdy
from urirun_contract import Contract, Wire

CONTRACTS = {
    "window/command/close": Contract(
        version="v1", effect="command", reversible=True,
        inverse_route="window/command/restore",
        inp={"id": "?str"},
        out={"action": "const:window-close", "snapshot": "obj", "inverse": "?obj"},
        errors=("unreachable",),
        examples=(...),
    ),
    "window/command/restore": Contract(...),
}
WIRES = [Wire("window/command/close", "window/command/restore", {"snapshot": "snapshot"})]
```

```python
# core.py — enforce() PRZED pierwszym @conn.handler
import os
import urirun
from urirun_contract import enforce
from myconnector.contracts import CONTRACTS

conn = urirun.connector("myconn", scheme="myscheme")
enforce(conn, CONTRACTS, validate=os.environ.get("URIRUN_CONTRACT_CHECK") == "1")

@conn.handler("window/command/close", isolated=True)
def close(id: str = "") -> dict:
    ...
```

## Pipeline (lokalnie, przed commitem)

```bash
make contract              # README → contracts.json  (LLM, bramkowane conform())
make gen                   # contracts.json → src/handlers_generated.py
make check                 # conform + anty-dryf (bez LLM)
pre-commit install         # wepnij bramy w git
```

## API

| Funkcja | Opis |
|---------|------|
| `Contract` | Deklaracja trasy: efekt, reversible, inp, out, errors, examples |
| `Wire` | Krawędź kompozycji: producer → consumer + mapping |
| `conform(contracts)` | Oracle CI: efekt↔czasownik, wzajemny inverse, golden examples |
| `enforce(conn, contracts, validate=...)` | Wrap `conn.handler` przed dekoratorami |
| `check(schema, value, where)` | Walidator mini-języka schematu |
| `check_wire(wire, contracts)` | Statyczna weryfikacja krawędzi kompozycji |
| `envelope_violation(contract, envelope)` | Sprawdź kopertę; zwróć naruszenie lub None |

### Mini-język schematu

| Token | Znaczenie |
|-------|-----------|
| `"str"` `"int"` `"bool"` `"num"` `"obj"` `"list"` `"any"` | typy prymitywne |
| `"?str"` | opcjonalny / nullable |
| `"const:write"` | dokładna wartość literalna |
| `"enum:a\|b\|c"` | wartość z listy |
| `["int"]` | jednorodna lista |
| `{"oneOf": [A, B]}` | unia wariantów |

## CI (deterministyczne, bez LLM)

```yaml
# .github/workflows/contract.yml
- run: pip install urirun-contract pytest
- run: python -m pytest tests/ -q
- run: bash ci/pre_commit.sh
```

## Przykład

```
examples/windowpair/     — odwracalna para window/close ↔ window/restore
  contracts.json         — deklaracja (2 kontrakty + 1 wire)
  src/handlers_generated.py  — wygenerowany szkielet (nie edytuj ręcznie)
```

## Licencja

Apache-2.0 · Tom Sapletta · https://tom.sapletta.com
