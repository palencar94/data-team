# ITBI SP — Medallion Architecture

**dbt project name:** `itbi_sp`
**Database:** DuckDB (single file at `$DB_PATH`, set in `.env`)
**Default schema:** `main`

---

## Layer Overview

```
data/GUIAS DE ITBI PAGAS (2).xlsx  ──► scripts/ingest.py ──► raw_itbi_transactions (DuckDB table)
data/cep_sp.csv                    ──► scripts/load_cep_lookup.py ──► raw_cep_lookup (DuckDB table)

                    [Bronze layer — dbt views]
        raw_itbi_transactions ──► bronze_itbi_transactions
        raw_cep_lookup        ──► bronze_cep_lookup

                    [Seeds — dbt tables]
        seed_uso_lookup    (36 rows — use code → description/category)
        seed_padrao_lookup (32 rows — construction standard → description/category)

                    [Silver layer — dbt table]
        bronze_itbi_transactions + bronze_cep_lookup + seeds ──► silver_itbi_transactions

                    [Gold layer — dbt tables]
        silver_itbi_transactions ──► gold_itbi_monthly_summary
                                 ──► gold_itbi_neighborhood_ranking
                                 ──► gold_itbi_price_per_m2
```

---

## Raw Tables (DuckDB, populated by Python scripts)

### `raw_itbi_transactions`
Populated by `scripts/ingest.py`. All columns are VARCHAR except `source_sheet VARCHAR NOT NULL` and `ingested_at TIMESTAMP NOT NULL`. Full schema in `scripts/ingest.py` `CREATE_BRONZE_DDL`.

Idempotent: re-running for the same sheet deletes existing rows for that sheet before inserting.

### `raw_cep_lookup`
Populated by `scripts/load_cep_lookup.py`. Columns: `cep, logradouro, lado, bairro, id_cidade, id_bairro` (all VARCHAR). `DROP TABLE IF EXISTS` before each load (full refresh).

---

## Bronze Layer (dbt views)

### `bronze_itbi_transactions`
`itbi_sp/models/bronze/bronze_itbi_transactions.sql`
Simple passthrough view: `SELECT * FROM raw_itbi_transactions`

### `bronze_cep_lookup`
`itbi_sp/models/bronze/bronze_cep_lookup.sql`
Simple passthrough view: `SELECT * FROM raw_cep_lookup`

---

## Seeds (dbt tables)

### `seed_uso_lookup`
Columns: `uso_codigo (VARCHAR), uso_descricao_canonical, uso_categoria`
Column type for `uso_codigo` is explicitly set to `varchar` in `dbt_project.yml` to prevent numeric coercion.

### `seed_padrao_lookup`
Columns: `padrao_codigo (VARCHAR), padrao_descricao_canonical, padrao_categoria`
Same `varchar` override for `padrao_codigo`.

---

## Silver Layer (dbt table, full refresh)

### `silver_itbi_transactions`
`itbi_sp/models/silver/silver_itbi_transactions.sql`

**Grain:** One row per ITBI transaction (filtered to valid positive transaction values with valid dates)
**Row count:** ~49,162 (after filtering invalid values)

**CTE pipeline:**
1. `typed` — TRY_CAST all numeric/date columns, extract `natureza_transacao_codigo` + `natureza_transacao_descricao`, filter `valor_transacao > 0 AND NOT NULL`
2. `typed_with_month` — add `month_year` (YYYY-MM), filter `data_transacao IS NOT NULL`
3. `cep_lookup` — deduplicate `bronze_cep_lookup` to 1 canonical `bairro` per CEP (ROW_NUMBER OVER PARTITION BY cep)
4. `cep_enriched` — LEFT JOIN `typed_with_month` with `cep_lookup` on `LPAD(REGEXP_REPLACE(cep, '[^0-9]', ''), 8, '0') = cep_lookup.cep`, adds `bairro_from_cep`
5. `normalized` — applies `normalize_bairro()` macro on `COALESCE(bairro_raw, bairro_from_cep)`, falls back to `'DESCONHECIDO'`
6. `uso_resolved` — LEFT JOIN with `seed_uso_lookup` to resolve `uso_codigo` → `uso_desc`, `uso_categoria`
7. `padrao_resolved` — LEFT JOIN with `seed_padrao_lookup` to resolve `padrao_codigo` → `padrao_desc`, `padrao_categoria`
8. `enriched` — final SELECT with MD5 `transaction_id` surrogate key and derived `price_per_m2`

---

## Gold Layer (dbt tables, full refresh)

### `gold_itbi_monthly_summary`
`itbi_sp/models/gold/gold_itbi_monthly_summary.sql`
**Grain:** One row per `month_year` (YYYY-MM)
**Key columns:** `monthly_summary_id, month_year, transaction_count, total_value_brl, kpi_median_price, kpi_median_price_per_m2, avg_price_per_m2, created_at`
**Purpose:** City-wide monthly trends (Chart A in dashboard)

### `gold_itbi_neighborhood_ranking`
`itbi_sp/models/gold/gold_itbi_neighborhood_ranking.sql`
**Grain:** One row per `(bairro_normalized, month_year)`
**Key columns:** `neighborhood_month_id, bairro_normalized, month_year, transaction_count, kpi_median_price, kpi_median_price_per_m2, kpi_mom_price_change_pct, kpi_mom_price_per_m2_change_pct, created_at`
**Uses:** Window functions (LAG OVER PARTITION BY bairro_normalized ORDER BY month_year) for MoM metrics
**Purpose:** Neighborhood ranking and appreciation (Charts B in dashboard)

### `gold_itbi_price_per_m2`
`itbi_sp/models/gold/gold_itbi_price_per_m2.sql`
**Grain:** One row per `(bairro_normalized, uso_desc, month_year)` — only where `price_per_m2 IS NOT NULL`
**Key columns:** `price_m2_id, bairro_normalized, uso_desc, month_year, transaction_count, kpi_median_price_per_m2, kpi_avg_price_per_m2, created_at`
**Purpose:** Price/m² by use type and neighborhood (Charts C in dashboard)

---

## Macros

### `normalize_bairro(col)`
`itbi_sp/macros/normalize_bairro.sql`
Normalizes neighborhood name strings for consistent grouping:
1. `UPPER()` — uppercase
2. 31 nested `REPLACE()` — strip accents (ã→a, â→a, ê→e, í→i, etc.)
3. `TRIM(REGEXP_REPLACE(..., '\s+', ' '))` — collapse multiple spaces
4. 14 `REGEXP_REPLACE()` wrappers — expand abbreviations (JD→JARDIM, VL→VILA, PQ→PARQUE, etc.)

**Critical:** This macro has 31 REPLACE( opens and 31 replacement patterns — they must stay balanced. A previous bug had a stray `)` on the `TRIM(REGEXP_REPLACE(...)` line.

---

## Data Quality (Soda Core)

**Config:** `itbi_sp/soda/configuration.yml`
**Checks directory:** `itbi_sp/soda/checks/`

- `bronze_privacy_guard.yml` — fails if `cartorio_de_registro` or `matricula_do_imovel` appear in `raw_itbi_transactions`
- `bronze_itbi_transactions.yml` — freshness, row count, not-null checks, composite key uniqueness (warn)

Soda exits with code 1 for warnings, 2+ for failures. The Makefile `soda-bronze` target allows exit code 1 (`if [ $EXIT -gt 1 ]; then exit $EXIT; fi`).
