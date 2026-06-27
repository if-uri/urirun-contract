# urirun-contract-windowpair

**Format `urirun-contract-*`: README opisuje intencję, lokalny LLM proponuje kontrakt,
generator deterministycznie robi kod, bramy egzekwują — CI tylko weryfikuje.**

## Co ten projekt robi (źródło intencji dla LLM)

Dwie operacje URI tworzące **odwracalną parę między procesami**:

- `window/command/close` — **command, odwracalne**. Robi snapshot stanu aktywnego okna
  (URL, scroll, pola formularzy), zwraca go jako `snapshot`, potem zamyka okno. Zwraca też
  `inverse` wskazujący `window/command/restore` z tym snapshotem jako argumentem.
- `window/command/restore` — **command, odwracalne**, inverse dla `close`. Przyjmuje
  `snapshot`, nawiguje do jego URL i rehydratuje scroll oraz pola.

Snapshot z `close` jest **kompletnym** wejściem `restore` (pełny handoff). Proces A może
zamknąć okno, a proces B — czytając tylko JSON snapshotu — odtworzyć je. Łączy ich wyłącznie
kontrakt, nie współdzielony obiekt.

Błędy, które te trasy mogą emitować: `cdp-unreachable`, `snapshot-url-missing`.

## Pipeline

```
README.md  ──(lokalny LLM via LiteLLM)──▶  contracts.json  ──(generator det.)──▶  src/handlers_generated.py
   intencja        proponuje, człowiek            kształt prawdy           sygnatura + koperta (nie edytuj ręcznie)
                   recenzuje + commituje                                          │
                                                                                  ▼  człowiek/LLM pisze CIAŁO
                                                                            src/handlers.py
                                                                                  │
                                                                                  ▼  enforce + conform (det.)
                                                                            registry (bindings.v2)
```

Dwa kroki LLM (NL→kontrakt, ciało) są **bramkowane**; generator w środku jest deterministyczny.
LLM nigdy nie biegnie w CI — proponuje lokalnie, CI tylko weryfikuje.

## Lokalnie, przed commitem

```bash
make contract              # LLM: README → contracts.json (bramkowane: conform odrzuca zły kontrakt)
make gen                   # contracts.json → src/handlers_generated.py
make check                 # regen-check (brak ręcznego dryfu) + conform + kompozycja + międzyproces
pre-commit install         # wepnij bramy w git (uruchamiają się przy każdym commit)
```

## CI/CD

Workflow `.github/workflows/contract.yml` uruchamia **te same** bramy co pre-commit —
deterministycznie, bez LLM. Kontrakt i wygenerowany kod są w repo i recenzowane w PR.

## Wariant wielopakietowy (dwa procesy, transport, Docker)

Ten sam `contracts.json` napędza dwa NIEZALEŻNIE wdrażane pakiety gadające po HTTP:

```
packages/producer/  → serwis HTTP: window/command/close   (enforce wyjścia na granicy)
packages/consumer/  → serwis HTTP: window/command/restore  (enforce wejścia na granicy)
orchestrator/       → woła producenta, stosuje krawędź WIRES, woła konsumenta, waliduje
toolkit/            → JEDNO źródło bramy, kopiowane do każdego obrazu (jak pip install)
```

Każdy serwis ładuje wspólny kontrakt niezależnie i egzekwuje go na granicy transportu —
konsument odrzuca każdy payload niezgodny z `restore.inp` (czyjkolwiek by nie był).

```bash
# lokalnie (bez dockera):
PORT=8801 python packages/producer/service.py &
PORT=8802 python packages/consumer/service.py &
python orchestrator/drive.py

# w kontenerach — orchestrator zwraca kod CI po sieci:
docker compose up --build --abort-on-container-exit --exit-code-from orchestrator
```
