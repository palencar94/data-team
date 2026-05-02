# ITBI SP — Pipeline Runbook

---

## Prerequisites

- Python 3.9 (system Python on this machine)
- `.env` file at project root with `DB_PATH=workspace/2026-05-01-itbi-sp-dashboard/build/itbi_sp.duckdb`
- `.venv/` created via `make venv` and dependencies installed via `make install`
- Source XLSX at `data/GUIAS DE ITBI PAGAS (2).xlsx`
- CEP lookup at `data/cep_sp.csv`

---

## Makefile Targets

Run from the project root (`/Users/pauloguilhermealencar/Documents/Projetos-Claude/data-team/`).

| Target | Command | What it does |
|--------|---------|-------------|
| `venv` | `make venv` | Create `.venv` with `python -m venv .venv` |
| `install` | `make install` | Install all dependencies from `requirements.txt` into `.venv` |
| `dbt-deps` | `make dbt-deps` | Install dbt packages (`dbt_utils`) |
| `ingest` | `make ingest` | Run `scripts/ingest.py` — load XLSX sheets matching `^[A-Z]{3}-\d{4}$` into `raw_itbi_transactions` |
| `load-cep` | `make load-cep` | Run `scripts/load_cep_lookup.py` — load `data/cep_sp.csv` into `raw_cep_lookup` |
| `soda-bronze` | `make soda-bronze` | Run Soda Core privacy guard + DQ checks on Bronze layer |
| `dbt-seed` | `make dbt-seed` | Load `seed_uso_lookup` and `seed_padrao_lookup` into DuckDB |
| `dbt-run` | `make dbt-run` | Build all dbt models (Bronze views + Silver + Gold tables) |
| `dbt-test` | `make dbt-test` | Run all 46 dbt tests |
| `serve` | `make serve` | Launch Streamlit dashboard on `http://localhost:8501` |
| `pipeline` | `make pipeline` | Run full pipeline: ingest → load-cep → soda-bronze → dbt-seed → dbt-run → dbt-test |
| `clean` | `make clean` | Remove `itbi_sp/target/`, `itbi_sp/logs/`, old log files |

---

## Full First-Run Setup

```bash
make venv
source .venv/bin/activate
make install
make dbt-deps
make pipeline
make serve
```

---

## Adding a New Monthly Sheet

1. Open `data/GUIAS DE ITBI PAGAS (2).xlsx` and ensure the new sheet is named `MMM-YYYY` (e.g., `ABR-2026`)
2. Run `make ingest` — it auto-detects sheets matching the pattern, idempotently deletes and re-inserts
3. Run `make dbt-run` to refresh Silver and Gold layers
4. The dashboard picks up the new month automatically

No code changes required.

---

## Environment Variables

Set in `.env` at project root:

```
DB_PATH=workspace/2026-05-01-itbi-sp-dashboard/build/itbi_sp.duckdb
```

The Makefile includes `.env` and exports all variables so dbt and Python scripts inherit `DB_PATH`.

dbt reads `DB_PATH` via `env_var('DB_PATH')` in `itbi_sp/profiles.yml`.

---

## DuckDB Concurrency Warning

**DuckDB only allows one writer at a time.** If Streamlit is running and holding the database open, any ingestion or dbt run will fail with:

```
IOException: IO Error: Could not set lock on file "...itbi_sp.duckdb"
```

**Fix:** Stop Streamlit before running the pipeline.
```bash
pkill -f "streamlit run"
make pipeline
make serve  # restart after pipeline completes
```

---

## dbt Project Structure

```
itbi_sp/
  dbt_project.yml        — project config, seed column type overrides, model materializations
  profiles.yml           — DuckDB connection using $DB_PATH
  packages.yml           — dbt_utils dependency
  macros/
    normalize_bairro.sql — bairro normalization macro (31 REPLACE + 14 REGEXP_REPLACE)
  models/
    bronze/              — views over raw tables
    silver/              — silver_itbi_transactions (table)
    gold/                — 3 gold tables
  seeds/
    seed_uso_lookup.csv
    seed_padrao_lookup.csv
  soda/
    configuration.yml
    checks/
```

---

## Log Files

Ingestion logs are written to `logs/ingestion_<timestamp>.log`. Old logs (>7 days) are removed by `make clean`.
