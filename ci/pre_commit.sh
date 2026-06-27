#!/usr/bin/env bash
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
# Bramy lokalne PRZED commitem — te same co w CI (deterministyczne, bez LLM).
set -euo pipefail
cd "$(dirname "$0")/.."
export URIRUN_CONTRACT_CHECK=1

echo "== 1/4 jedno źródło kernela (gate/codegen def w 1 miejscu; reszta re-eksport) =="
python -m urirun_contract.check_single_source .

echo "== 2/4 pokrycie floty kontraktami (ratchet: brak nowych mutujących bez kontraktu) =="
python ci/fleet_coverage.py .. --baseline ci/fleet_coverage.baseline.json

# Kroki 2-3 dotyczą PROJEKTU z własnym contracts.json. urirun-contract to BIBLIOTEKA (bramy/codegen),
# nie wozi projektowego kontraktu w korzeniu (patrz roadmap: jeden contracts.json per projekt) —
# więc gdy go nie ma, pomijamy je czysto zamiast pękać na brakującym pliku.
if [ -f contracts.json ]; then
  echo "== 3/4 kontrakt konformuje (efekt, wzajemny inverse, przykłady) =="
  python ci/nl_to_contract.py --validate contracts.json
  echo "== 4/4 wygenerowany kod zgodny z kontraktem (anty-dryf) =="
  python ci/regen_check.py
else
  echo "== 3-4/4 pominięte: brak projektowego contracts.json w korzeniu (to biblioteka, nie projekt) =="
fi

# Przykład windowpair JEST projektem-pod-testem tej biblioteki — egzekwuj te same bramy co CI.
if [ -f examples/windowpair/contracts.json ]; then
  echo "== windowpair: konformans + anty-dryf + additive-only (te same bramy co CI) =="
  python ci/nl_to_contract.py --validate examples/windowpair/contracts.json
  python ci/regen_check.py examples/windowpair/contracts.json examples/windowpair/src/handlers_generated.py
  python ci/check_compat.py examples/windowpair/contracts.baseline.json examples/windowpair/contracts.json
fi

echo
echo "OK: gotowe do commitu."
