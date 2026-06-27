.PHONY: help test contract gen check lint install integration single-source conformance
PY ?= python
export URIRUN_CONTRACT_CHECK = 1
CONTRACTS ?= examples/windowpair/contracts.json

help: ## Lista celów
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-12s %s\n",$$1,$$2}'

install: ## pip install -e .
	pip install -e .

test: ## pytest tests/
	$(PY) -m pytest tests/ -q

contract: ## README.md → contracts.json (lokalny LLM, bramkowane)
	$(PY) ci/nl_to_contract.py

gen: ## contracts.json → src/handlers_generated.py
	$(PY) ci/emit_handlers.py

check: ## wszystkie bramy lokalne (bez LLM, te same co CI)
	bash ci/pre_commit.sh

lint: ## CC gate (radon -n D)
	radon cc -n D urirun_contract/

single-source: ## CI: kernel (gate/codegen) zdefiniowany w JEDNYM miejscu; reszta to re-eksport
	$(PY) -m urirun_contract.check_single_source .

conformance: ## Driver bije w żywy węzeł (peer serve-http) i waliduje koperty z drutu
	@CONTRACTS=$(CONTRACTS) $(PY) xlang/peer.py serve-http > /tmp/_peer.out 2>&1 & P=$$!; \
	 for i in $$(seq 1 40); do PORT=$$(sed -n 's/^READY //p' /tmp/_peer.out); [ -n "$$PORT" ] && break; sleep 0.1; done; \
	 CONTRACTS=$(CONTRACTS) $(PY) adapters/conformance.py --node http://127.0.0.1:$$PORT --no-wait; CODE=$$?; \
	 kill $$P 2>/dev/null; exit $$CODE

integration: ## Test HTTP end-to-end (py→py + py→go) bez Dockera
	@CONTRACTS=contracts.json PORT=8801 $(PY) packages/producer/service.py & P1=$$!; \
	 CONTRACTS=contracts.json PORT=8802 $(PY) packages/consumer/service.py & P2=$$!; \
	 go build -C packages/consumer-go -o /tmp/_consumer-go . && CONTRACTS=$$PWD/contracts.json PORT=8803 /tmp/_consumer-go & P3=$$!; \
	 sleep 2; \
	 CONTRACTS=contracts.json CONSUMER_GO_URL=http://localhost:8803 $(PY) orchestrator/drive.py; CODE=$$?; \
	 kill $$P1 $$P2 $$P3 2>/dev/null; exit $$CODE
