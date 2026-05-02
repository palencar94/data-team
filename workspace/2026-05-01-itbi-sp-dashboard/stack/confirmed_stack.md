# Confirmed Tech Stack

Request: 2026-05-01-itbi-sp-dashboard
Confirmed: 2026-05-01

## Storage
DuckDB (>= 0.10.x, latest stable)
- Single-file embedded database, zero server setup, local machine deployment
- .duckdb file path set via environment variable, excluded from git

## Transform
dbt core + dbt-duckdb adapter (dbt-duckdb >= 1.7, pulls dbt-core as transitive dependency)
- Bronze → Silver → Gold medallion architecture
- Silver layer includes an explicit standardization sub-step (see below)

## Standardization (Silver layer — within dbt)
Explicit Silver dbt models for:
- Neighborhood name normalization: strip accents, uppercase, collapse abbreviations (JD → JARDIM, etc.)
- Property type code resolution: join to Tabela de USOS / Tabela de PADRÕES lookup tables
- Portuguese text encoding cleanup: handle special characters in street names and neighborhood fields
- Derived field: price_per_m2 = transaction_value / built_area_m2 (null-safe)
This is not a separate tool — it is a mandatory design requirement for the Silver layer dbt models.

## Orchestration
Makefile (no orchestration daemon)
- Targets: make ingest → make transform → make test → make serve
- Explicit .venv/bin/python paths in all recipes (shell activation does not persist across make recipe lines)
- make serve opens DuckDB in read-only mode to prevent lock conflicts

## BI / Viz
Streamlit (>= 1.32.x)
- Local web server, connects to DuckDB in read-only mode
- @st.cache_data on all query functions

## Data Quality
Two-layer DQ strategy:
1. Soda Core with soda-core-duckdb (post-ingestion Bronze checks): volume checks, null rates, schema assertions, privacy field absence
2. dbt tests (built-in, post-transform Silver/Gold checks): not_null, unique, accepted_values, relationship tests
- Soda Core checks run as part of make test before dbt run
- dbt test runs after dbt run; test failures halt the pipeline

## Ingestion
Python + openpyxl (openpyxl >= 3.x)
- XLSX sheet auto-detection via regex ^[A-Z]{3}-\d{4}$
- Privacy fields excluded before any row is written to DuckDB (exclusion list from LEGENDA sheet)
- polars available as fallback if pre-write transforms are needed

## Virtual Environment
Python 3.11.x
All dependencies installed inside .venv — no global installs
```
requirements.txt (indicative — Engineer finalizes in build phase):
dbt-duckdb>=1.7.0
streamlit>=1.32.0
soda-core-duckdb>=3.0.0
openpyxl>=3.1.0
python-dotenv>=1.0.0
```
