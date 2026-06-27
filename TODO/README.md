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
