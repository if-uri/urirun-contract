# windowpair — przykład urirun-contract

**Dwie operacje URI tworzące odwracalną parę między procesami:**

- `window/command/close` — zamknij okno, zwróć snapshot stanu (URL, scroll, formularze)
- `window/command/restore` — odtwórz okno z snapshotu (nawigacja URL + rehydratacja stanu)

Snapshot z `close` jest kompletnym wejściem `restore`. Proces A może zamknąć okno,
a proces B — czytając tylko JSON snapshotu — odtworzyć je. Łączy je wyłącznie kontrakt.

## Uruchom

```bash
pip install urirun-contract
# wygeneruj handlers_generated.py z contracts.json
python -m urirun_contract.codegen all-py contracts.json src/handlers_generated.py
# sprawdź kontrakt
python ci/nl_to_contract.py --validate contracts.json
# sprawdź anty-dryf
python ci/regen_check.py
```
