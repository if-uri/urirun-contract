.PHONY: help test contract gen check lint install
PY ?= python
export URIRUN_CONTRACT_CHECK = 1

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
