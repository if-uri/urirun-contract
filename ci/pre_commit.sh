#!/usr/bin/env bash
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
# Bramy lokalne PRZED commitem — te same co w CI (deterministyczne, bez LLM).
set -euo pipefail
cd "$(dirname "$0")/.."
export URIRUN_CONTRACT_CHECK=1

echo "== 1/3 jedno źródło kernela (gate/codegen def w 1 miejscu; reszta re-eksport) =="
python -m urirun_contract.check_single_source .

# Kroki 2-3 dotyczą PROJEKTU z własnym contracts.json. urirun-contract to BIBLIOTEKA (bramy/codegen),
# nie wozi projektowego kontraktu w korzeniu (patrz roadmap: jeden contracts.json per projekt) —
# więc gdy go nie ma, pomijamy je czysto zamiast pękać na brakującym pliku.
if [ -f contracts.json ]; then
  echo "== 2/3 kontrakt konformuje (efekt, wzajemny inverse, przykłady) =="
  python ci/nl_to_contract.py --validate contracts.json
  echo "== 3/3 wygenerowany kod zgodny z kontraktem (anty-dryf) =="
  python ci/regen_check.py
else
  echo "== 2-3/3 pominięte: brak projektowego contracts.json w korzeniu (to biblioteka, nie projekt) =="
fi

echo
echo "OK: gotowe do commitu."
