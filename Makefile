# Load .env variables into the Make environment
ifneq (,$(wildcard .env))
  include .env
  export
endif

.PHONY: venv install ingest load-cep soda-bronze dbt-deps dbt-seed dbt-run dbt-test serve pipeline clean help

PYTHON    = .venv/bin/python
DBT       = .venv/bin/dbt
SODA      = .venv/bin/soda
STREAMLIT = .venv/bin/streamlit

DBT_PROJECT_DIR  = itbi_sp
DBT_PROFILES_DIR = itbi_sp
SODA_CONFIG      = itbi_sp/soda/configuration.yml
XLSX_FILE        = data/GUIAS DE ITBI PAGAS (2).xlsx

## ──────────────────────────────────────────────────────────────────────────
## Setup
## ──────────────────────────────────────────────────────────────────────────

venv: ## Create virtual environment (.venv)
	python -m venv .venv
	@echo "Run: source .venv/bin/activate"

install: ## Install all Python dependencies inside .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

dbt-deps: ## Install dbt packages (dbt_utils)
	$(DBT) deps \
	  --project-dir $(DBT_PROJECT_DIR) \
	  --profiles-dir $(DBT_PROFILES_DIR)

## ──────────────────────────────────────────────────────────────────────────
## Pipeline steps
## ──────────────────────────────────────────────────────────────────────────

ingest: ## Ingest XLSX into DuckDB Bronze layer
	$(PYTHON) scripts/ingest.py --file "$(XLSX_FILE)"

load-cep: ## Load data/cep_sp.csv into DuckDB as raw_cep_lookup
	$(PYTHON) scripts/load_cep_lookup.py

soda-bronze: ## Run Soda Core DQ checks on Bronze layer (exit 1=warnings OK, exit 2+=failures block)
	$(SODA) scan \
	  -d itbi_duckdb \
	  -c $(SODA_CONFIG) \
	  itbi_sp/soda/checks/bronze_privacy_guard.yml; \
	  EXIT=$$?; if [ $$EXIT -gt 1 ]; then exit $$EXIT; fi
	$(SODA) scan \
	  -d itbi_duckdb \
	  -c $(SODA_CONFIG) \
	  itbi_sp/soda/checks/bronze_itbi_transactions.yml; \
	  EXIT=$$?; if [ $$EXIT -gt 1 ]; then exit $$EXIT; fi

dbt-seed: ## Load seed lookup tables (uso + padrao)
	$(DBT) seed \
	  --project-dir $(DBT_PROJECT_DIR) \
	  --profiles-dir $(DBT_PROFILES_DIR)

dbt-run: ## Run all dbt models (Silver + Gold)
	$(DBT) run \
	  --project-dir $(DBT_PROJECT_DIR) \
	  --profiles-dir $(DBT_PROFILES_DIR)

dbt-test: ## Run all dbt tests (not_null, unique, RI, business rules)
	$(DBT) test \
	  --project-dir $(DBT_PROJECT_DIR) \
	  --profiles-dir $(DBT_PROFILES_DIR)

serve: ## Launch Streamlit dashboard (read-only Gold layer)
	$(STREAMLIT) run app/streamlit_app.py

## ──────────────────────────────────────────────────────────────────────────
## Full pipeline (ordered, fail-fast)
## ──────────────────────────────────────────────────────────────────────────

pipeline: ingest load-cep soda-bronze dbt-seed dbt-run dbt-test ## Run full pipeline (ingest → CEP lookup → DQ → seeds → transform → test)
	@echo "Pipeline complete. Run 'make serve' to start the dashboard."

## ──────────────────────────────────────────────────────────────────────────
## Maintenance
## ──────────────────────────────────────────────────────────────────────────

clean: ## Remove dbt target artifacts and logs older than 7 days
	rm -rf itbi_sp/target itbi_sp/logs
	find logs/ -name "*.log" -mtime +7 -delete 2>/dev/null || true

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
