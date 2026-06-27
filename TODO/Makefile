# urirun-contract-windowpair — bramy kontraktowe
PY ?= python
export URIRUN_CONTRACT_CHECK = 1

contract:            ## README → contracts.json (lokalny LLM, bramkowane)
	@$(PY) ci/nl_to_contract.py

gen:                 ## contracts.json → src/handlers_generated.py
	@$(PY) gen/emit_handlers.py

check:               ## wszystkie bramy (to samo co CI)
	@bash ci/pre_commit.sh

.PHONY: contract gen check
