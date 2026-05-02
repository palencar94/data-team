# Model Specification
## Request ID: 2026-05-01-itbi-sp-dashboard

---

## Business Context

This model supports a real estate investment analysis dashboard for São Paulo, driven by ITBI (Imposto sobre Transmissão de Bens Imóveis) transaction data. The pipeline answers three core business questions:

1. How have building transaction prices evolved month-over-month in 2026?
2. Which neighborhoods (bairros) have seen the highest price appreciation?
3. What is the price per m² trend by area and property use type?

The ITBI dataset is published monthly by Prefeitura de São Paulo as a multi-sheet XLSX workbook. New monthly sheets must be processed automatically on file drop with no pipeline code changes. The confirmed stack is DuckDB + dbt-core (dbt-duckdb adapter) + Python/openpyxl ingestion + Soda Core DQ + Streamlit dashboard, orchestrated via Makefile.

---

## Grain

| Model | Grain |
|---|---|
| `bronze_itbi_transactions` | One row per source row per XLSX worksheet tab — no dedup, no transformation |
| `silver_itbi_transactions` | One row per unique qualifying transaction (valor_transacao > 0), deduplicated by deterministic surrogate key |
| `gold_itbi_monthly_summary` | One row per calendar month (YYYY-MM) across all transactions |
| `gold_itbi_neighborhood_ranking` | One row per (bairro_normalized, month_year) combination |
| `gold_itbi_price_per_m2` | One row per (bairro_normalized, uso_desc, month_year) combination |

---

## Entities and Relationships

**Core entities:**
- **Transaction:** An ITBI property transfer event. Identified by sql_cadastro + data_transacao + valor_transacao + source_sheet. Central fact of the pipeline.
- **Property (implicit):** Identified by sql_cadastro (11-digit PMSP cadastral ID). Not materialized as a separate dimension; property attributes are carried on the transaction fact.
- **Neighborhood:** Identified by bairro_normalized (derived, not a source ID). Serves as a grouping dimension in Gold.
- **Use Type:** IPTU use code + canonical description from seed_uso_lookup. Dimension resolved at Silver.
- **Construction Standard:** IPTU padrão code + canonical description from seed_padrao_lookup. Dimension resolved at Silver.
- **Calendar Month:** month_year (YYYY-MM string) derived from data_transacao. Acts as the time dimension in Gold.

**Relationships:**
- `silver_itbi_transactions` → `seed_uso_lookup`: LEFT JOIN on uso_codigo (many transactions to one use type; NULL-safe — unresolved codes fall back to source description)
- `silver_itbi_transactions` → `seed_padrao_lookup`: LEFT JOIN on padrao_codigo (many transactions to one standard; NULL-safe)
- `gold_itbi_neighborhood_ranking` references `gold_itbi_monthly_summary` logically by month_year (no hard FK in DuckDB; validated via RI test in dbt)
- `gold_itbi_price_per_m2` references `gold_itbi_neighborhood_ranking` logically by (bairro_normalized, month_year)

---

## Layer Design

### Bronze — `bronze_itbi_transactions`

**Inputs:**
- Raw XLSX file at `data/raw/itbi_sp_2026.xlsx` (or any file matching the configured glob pattern)
- All worksheets auto-detected at runtime by the Python ingestion script
- Sheets named LEGENDA, EXPLICAÇÕES, Tabela de USOS, Tabela de PADRÕES are excluded from transaction ingestion (handled separately for seed preparation)

**Ingestion script behavior (Python + openpyxl):**
1. Open workbook; enumerate all sheet names
2. For each sheet whose name matches the month pattern (e.g. `[A-Z]{3}-[0-9]{4}`):
   a. Read all rows starting from the header row
   b. Map column names to the 26 retained field names (by name, not by index)
   c. **Explicitly skip columns "Cartório de Registro" and "Matrícula do Imóvel" — never read their values**
   d. Append `source_sheet = <sheet_name>` and `ingested_at = utcnow()` to each row
   e. Write rows to `bronze_itbi_transactions` in DuckDB using APPEND mode (idempotent: if sheet was already ingested, delete existing rows for that source_sheet first, then re-insert)
3. Log row counts per sheet to `logs/ingestion_<timestamp>.log`

**Minimal transforms applied in Bronze (all others deferred to Silver):**
- Strip leading/trailing whitespace from all string values
- Represent empty cells as NULL (not empty string)
- No type casting — all business columns stored as VARCHAR
- No filtering, no dedup, no business logic

**Soda Core DQ checks on Bronze (run after ingestion, before dbt):**
- `not_null` on: sql_cadastro, bairro, natureza_transacao, valor_transacao, data_transacao, source_sheet, ingested_at
- `no_duplicate_count` on: (sql_cadastro, data_transacao, valor_transacao, source_sheet) — severity HIGH (warn, do not block)
- Row count per source_sheet >= 100 (sanity floor — alert if sheet appears nearly empty)
- `freshness` on ingested_at: warn if max(ingested_at) < now() - 35 days

---

### Silver — `silver_itbi_transactions`

Silver is a single dbt model that executes two logical sub-steps in sequence within the same model transformation. The sub-steps are documented separately for clarity but produce one output table.

#### Sub-step 1: Typing and Cleaning

**Source:** `bronze_itbi_transactions`

**Casting rules:**
| Bronze field | Silver field | Cast | Null handling |
|---|---|---|---|
| sql_cadastro | sql_cadastro | VARCHAR (no change) | NOT NULL |
| bairro | bairro_raw | VARCHAR | NOT NULL |
| valor_transacao | valor_transacao | DECIMAL(18,2) via TRY_CAST | NULL on parse failure; rows with NULL or <= 0 filtered out |
| data_transacao | data_transacao | DATE via TRY_CAST | NULL on parse failure |
| valor_venal_referencia | valor_venal_referencia | DECIMAL(18,2); 0 → NULL | YES |
| proporcao_transmitida_pct | proporcao_transmitida_pct | DECIMAL(5,2) | YES |
| valor_venal_proporcional | valor_venal_proporcional | DECIMAL(18,2); 0 → NULL | YES |
| base_calculo | base_calculo | DECIMAL(18,2) | YES |
| valor_financiado | valor_financiado | DECIMAL(18,2) | YES |
| area_terreno_m2 | area_terreno_m2 | DECIMAL(12,2) | YES |
| testada_m | testada_m | DECIMAL(10,2) | YES |
| fracao_ideal | fracao_ideal | DECIMAL(10,6) | YES |
| area_construida_m2 | area_construida_m2 | DECIMAL(12,2) | YES |
| uso_iptu_codigo | uso_codigo | VARCHAR | YES |
| padrao_iptu_codigo | padrao_codigo | VARCHAR | YES |
| acc_iptu | acc_iptu | TRY_CAST INTEGER | YES |

**Natureza de Transação parsing:**
- Extract numeric prefix: `REGEXP_EXTRACT(natureza_transacao, '^([0-9]+)\.', 1)` → `natureza_transacao_codigo`
- Remainder: `REGEXP_REPLACE(natureza_transacao, '^[0-9]+\.\s*', '')` → `natureza_transacao_descricao`

**Derived field — month_year:**
- `STRFTIME(data_transacao, '%Y-%m')` → `month_year`

**Filter applied in Sub-step 1:**
- Exclude rows where `TRY_CAST(valor_transacao AS DECIMAL) IS NULL OR TRY_CAST(valor_transacao AS DECIMAL) <= 0`

#### Sub-step 2: Standardization (MANDATORY)

Executed within the same dbt Silver model, after Sub-step 1 CTE.

**2a. Neighborhood Name Normalization (`bairro_normalized`):**

Applied as a DuckDB SQL expression chain on `bairro_raw`:

1. Strip accents: replace accented characters using `REPLACE()` chains (ã→a, â→a, à→a, á→a, ê→e, é→e, í→i, õ→o, ó→o, ô→o, ú→u, ç→c, etc.) — DuckDB does not have a built-in `unaccent`; use a macro or explicit REPLACE chain
2. Uppercase: `UPPER()`
3. Trim and collapse multiple spaces: `TRIM(REGEXP_REPLACE(str, '\s+', ' '))`
4. Expand abbreviations using CASE/REPLACE in defined order (longer patterns first to avoid partial matches):

| Pattern (word-boundary match) | Expansion |
|---|---|
| `\bJD\b` | JARDIM |
| `\bJARD\b` | JARDIM |
| `\bVL\b` | VILA |
| `\bV\b` (standalone) | VILA |
| `\bPQ\b` | PARQUE |
| `\bPQE\b` | PARQUE |
| `\bCH\b` | CHACARA |
| `\bCHAC\b` | CHACARA |
| `\bLT\b` | LOTEAMENTO |
| `\bNUCLEO\b` | NUCLEO |
| `\bNCL\b` | NUCLEO |
| `\bCONJ\b` | CONJUNTO |
| `\bCJTO\b` | CONJUNTO |
| `\bST\b` | SETOR |

Implementation note: DuckDB `REGEXP_REPLACE` with word boundaries (`\b`) is used. A dbt macro `normalize_bairro(col)` encapsulates the full chain and is reused across models.

**2b. Use and Standard Code Resolution:**
- `LEFT JOIN {{ ref('seed_uso_lookup') }} ON uso_codigo = uso_codigo` → `uso_desc` (canonical); fallback `COALESCE(lookup.uso_descricao_canonical, bronze.uso_iptu_descricao)`
- `LEFT JOIN {{ ref('seed_padrao_lookup') }} ON padrao_codigo = padrao_codigo` → `padrao_desc` (canonical); fallback to source description
- JOINs are LEFT to preserve transactions with unresolved codes (code absence is not a filter criterion)

**2c. Portuguese Text Encoding Cleanup:**
- DuckDB reads UTF-8 natively via openpyxl; no re-encoding required at DB level
- Ingestion script must open the XLSX with `openpyxl` (UTF-8 safe) and write to DuckDB via Python's `duckdb` connector — do not use CSV intermediary to avoid encoding issues
- Residual mojibake in source strings (if any) is flagged by a Soda Core test on silver: `invalid_count` on bairro_normalized matching `[^\x00-\x7F\xC0-\xFF]` exotic codepoints → severity MEDIUM

**2d. Derived field — price_per_m2:**
```sql
CASE
  WHEN area_construida_m2 IS NULL OR area_construida_m2 = 0 THEN NULL
  ELSE ROUND(valor_transacao / area_construida_m2, 2)
END AS price_per_m2
```

**Surrogate key generation:**
```sql
md5(sql_cadastro || '|' || CAST(data_transacao AS VARCHAR) || '|' || CAST(valor_transacao AS VARCHAR) || '|' || source_sheet) AS transaction_id
```

Note: DuckDB `md5()` is used for simplicity; SHA-256 can be substituted if collision risk is a concern. The key must be deterministic and idempotent across re-runs.

**dbt model config:**
```yaml
models:
  - name: silver_itbi_transactions
    config:
      materialized: table
      contract:
        enforced: true
```

**dbt tests on Silver:**
- `not_null`: transaction_id, sql_cadastro, bairro_raw, bairro_normalized, natureza_transacao_codigo, valor_transacao, data_transacao, month_year, source_sheet
- `unique`: transaction_id — CRITICAL
- `accepted_values` on natureza_transacao_codigo: warn if unexpected non-numeric code appears
- `dbt_utils.expression_is_true`: `valor_transacao > 0` — CRITICAL
- `dbt_utils.expression_is_true`: `area_construida_m2 >= 0 OR area_construida_m2 IS NULL`
- `dbt_utils.expression_is_true`: `price_per_m2 > 0 OR price_per_m2 IS NULL`
- `relationships`: uso_codigo to seed_uso_lookup.uso_codigo — HIGH (warn on unresolved codes)
- `relationships`: padrao_codigo to seed_padrao_lookup.padrao_codigo — HIGH

---

### Gold — 3 Serving Tables

All Gold models are `materialized: table` in dbt. They read exclusively from `silver_itbi_transactions` and the seed lookups. They are the only layer exposed to the Streamlit dashboard.

#### `gold_itbi_monthly_summary`

**Purpose:** Month-over-month transaction volume and price trend across all São Paulo. Feeds the MoM evolution chart (Chart 1).

**Source:** `silver_itbi_transactions`

**Aggregation:**
```sql
SELECT
    md5(month_year) AS monthly_summary_id,
    month_year,
    COUNT(*)                             AS transaction_count,
    SUM(valor_transacao)                 AS total_value_brl,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY valor_transacao)    AS kpi_median_price,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_per_m2)
        FILTER (WHERE price_per_m2 IS NOT NULL)                     AS kpi_median_price_per_m2,
    AVG(price_per_m2) FILTER (WHERE price_per_m2 IS NOT NULL)       AS avg_price_per_m2,
    CURRENT_TIMESTAMP                    AS created_at
FROM silver_itbi_transactions
GROUP BY month_year
ORDER BY month_year
```

**dbt tests:**
- `not_null`: monthly_summary_id, month_year, transaction_count
- `unique`: monthly_summary_id — CRITICAL
- `dbt_utils.expression_is_true`: `transaction_count >= 1` — CRITICAL

---

#### `gold_itbi_neighborhood_ranking`

**Purpose:** Neighborhood-level price ranking and MoM appreciation. Feeds the neighborhood ranking chart (Chart 2) and the filterable bairro table.

**Source:** `silver_itbi_transactions`

**Aggregation + Window function for MoM:**
```sql
WITH base AS (
    SELECT
        bairro_normalized,
        month_year,
        COUNT(*)                                                                 AS transaction_count,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY valor_transacao)            AS kpi_median_price,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_per_m2)
            FILTER (WHERE price_per_m2 IS NOT NULL)                             AS kpi_median_price_per_m2
    FROM silver_itbi_transactions
    GROUP BY bairro_normalized, month_year
),
with_mom AS (
    SELECT
        *,
        LAG(kpi_median_price)       OVER (PARTITION BY bairro_normalized ORDER BY month_year) AS prev_median_price,
        LAG(kpi_median_price_per_m2) OVER (PARTITION BY bairro_normalized ORDER BY month_year) AS prev_median_price_per_m2
    FROM base
)
SELECT
    md5(bairro_normalized || '|' || month_year)  AS neighborhood_month_id,
    bairro_normalized,
    month_year,
    transaction_count,
    kpi_median_price,
    kpi_median_price_per_m2,
    CASE
        WHEN prev_median_price IS NULL OR prev_median_price = 0 THEN NULL
        ELSE ROUND(((kpi_median_price - prev_median_price) / prev_median_price) * 100, 4)
    END AS kpi_mom_price_change_pct,
    CASE
        WHEN prev_median_price_per_m2 IS NULL OR prev_median_price_per_m2 = 0 THEN NULL
        ELSE ROUND(((kpi_median_price_per_m2 - prev_median_price_per_m2) / prev_median_price_per_m2) * 100, 4)
    END AS kpi_mom_price_per_m2_change_pct,
    CURRENT_TIMESTAMP AS created_at
FROM with_mom
```

**Minimum transaction threshold:** Neighborhoods with `transaction_count < 3` in a month are included in the table but flagged — the Streamlit dashboard filters them from the ranking by default (configurable). This avoids ranking noise from single-transaction bairros.

**dbt tests:**
- `not_null`: neighborhood_month_id, bairro_normalized, month_year, transaction_count
- `unique`: neighborhood_month_id — CRITICAL
- `relationships`: month_year to gold_itbi_monthly_summary.month_year — HIGH
- `dbt_utils.expression_is_true`: `transaction_count >= 1`

---

#### `gold_itbi_price_per_m2`

**Purpose:** Price per m² drill-down by neighborhood and use type. Feeds the price/m² trend chart (Chart 3) and supports filtering by property type.

**Source:** `silver_itbi_transactions`

**Filter:** Only rows where `price_per_m2 IS NOT NULL` (i.e. area_construida_m2 > 0)

**Aggregation:**
```sql
SELECT
    md5(bairro_normalized || '|' || COALESCE(uso_desc, 'UNKNOWN') || '|' || month_year) AS price_m2_id,
    bairro_normalized,
    COALESCE(uso_desc, 'UNKNOWN')                                            AS uso_desc,
    month_year,
    COUNT(*)                                                                 AS transaction_count,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_per_m2)               AS kpi_median_price_per_m2,
    AVG(price_per_m2)                                                        AS kpi_avg_price_per_m2,
    CURRENT_TIMESTAMP                                                        AS created_at
FROM silver_itbi_transactions
WHERE price_per_m2 IS NOT NULL
GROUP BY bairro_normalized, COALESCE(uso_desc, 'UNKNOWN'), month_year
```

**dbt tests:**
- `not_null`: price_m2_id, bairro_normalized, uso_desc, month_year, transaction_count
- `unique`: price_m2_id — CRITICAL
- `dbt_utils.expression_is_true`: `kpi_median_price_per_m2 > 0`
- `relationships`: month_year to gold_itbi_monthly_summary.month_year — HIGH

---

## Keys and SCD

### Primary Keys

| Model | PK | Type | Generation |
|---|---|---|---|
| bronze_itbi_transactions | (sql_cadastro, data_transacao, valor_transacao, source_sheet) | Natural composite | Source values |
| silver_itbi_transactions | transaction_id | Surrogate VARCHAR | md5 of composite above |
| gold_itbi_monthly_summary | monthly_summary_id | Surrogate VARCHAR | md5 of month_year |
| gold_itbi_neighborhood_ranking | neighborhood_month_id | Surrogate VARCHAR | md5 of (bairro_normalized, month_year) |
| gold_itbi_price_per_m2 | price_m2_id | Surrogate VARCHAR | md5 of (bairro_normalized, uso_desc, month_year) |
| seed_uso_lookup | uso_codigo | Natural VARCHAR | Source lookup sheet |
| seed_padrao_lookup | padrao_codigo | Natural VARCHAR | Source lookup sheet |

### Foreign Keys (logical — validated by dbt RI tests, not enforced at DuckDB level)

| Child | FK Column(s) | Parent | Parent Column(s) |
|---|---|---|---|
| silver_itbi_transactions | uso_codigo | seed_uso_lookup | uso_codigo |
| silver_itbi_transactions | padrao_codigo | seed_padrao_lookup | padrao_codigo |
| gold_itbi_neighborhood_ranking | month_year | gold_itbi_monthly_summary | month_year |
| gold_itbi_price_per_m2 | month_year | gold_itbi_monthly_summary | month_year |

### SCD Strategy

- **No SCD applied** in this pipeline. ITBI transactions are immutable historical events — once declared, the source value does not change.
- **Re-ingestion strategy:** Bronze is fully refreshable per `source_sheet`. If a monthly sheet is corrected and re-dropped, the ingestion script deletes all rows for that `source_sheet` and re-inserts. Silver and Gold are rebuilt in full by dbt on each run (`materialized: table` — full refresh, not incremental).
- **Incremental optimization (future):** If data volume warrants it, Silver can be converted to `materialized: incremental` with `unique_key: transaction_id` and `on_schema_change: append_new_columns`. This is not implemented in v1 to keep the pipeline simple.
- **Lookup seed tables:** Versioned as static CSV seeds in `seeds/`. Changes to PMSP use/standard codes require manual seed update and a full Silver+Gold rebuild.

---

## Data Quality Rules

### Null Checks (dbt `not_null` tests — CRITICAL unless noted)

| Model | Column | Severity |
|---|---|---|
| bronze_itbi_transactions | sql_cadastro | CRITICAL |
| bronze_itbi_transactions | bairro | CRITICAL |
| bronze_itbi_transactions | natureza_transacao | CRITICAL |
| bronze_itbi_transactions | valor_transacao | CRITICAL |
| bronze_itbi_transactions | data_transacao | CRITICAL |
| bronze_itbi_transactions | source_sheet | CRITICAL |
| bronze_itbi_transactions | ingested_at | CRITICAL |
| silver_itbi_transactions | transaction_id | CRITICAL |
| silver_itbi_transactions | bairro_normalized | CRITICAL |
| silver_itbi_transactions | natureza_transacao_codigo | HIGH |
| silver_itbi_transactions | valor_transacao | CRITICAL |
| silver_itbi_transactions | data_transacao | CRITICAL |
| silver_itbi_transactions | month_year | CRITICAL |
| gold_itbi_monthly_summary | monthly_summary_id | CRITICAL |
| gold_itbi_monthly_summary | month_year | CRITICAL |
| gold_itbi_monthly_summary | transaction_count | CRITICAL |
| gold_itbi_neighborhood_ranking | neighborhood_month_id | CRITICAL |
| gold_itbi_neighborhood_ranking | bairro_normalized | CRITICAL |
| gold_itbi_neighborhood_ranking | month_year | CRITICAL |
| gold_itbi_price_per_m2 | price_m2_id | CRITICAL |
| gold_itbi_price_per_m2 | bairro_normalized | CRITICAL |
| gold_itbi_price_per_m2 | uso_desc | CRITICAL |
| gold_itbi_price_per_m2 | month_year | CRITICAL |

### Uniqueness Tests (dbt `unique` — all CRITICAL)

- `silver_itbi_transactions.transaction_id`
- `gold_itbi_monthly_summary.monthly_summary_id`
- `gold_itbi_neighborhood_ranking.neighborhood_month_id`
- `gold_itbi_price_per_m2.price_m2_id`
- `seed_uso_lookup.uso_codigo`
- `seed_padrao_lookup.padrao_codigo`

### Referential Integrity Tests (dbt `relationships` — HIGH)

- `silver.uso_codigo` → `seed_uso_lookup.uso_codigo`: LEFT JOIN acceptable; unresolved codes are allowed but counted and reported
- `silver.padrao_codigo` → `seed_padrao_lookup.padrao_codigo`: same
- `gold_neighborhood_ranking.month_year` → `gold_monthly_summary.month_year`
- `gold_price_per_m2.month_year` → `gold_monthly_summary.month_year`

### Business Logic Tests (dbt `dbt_utils.expression_is_true`)

| Test | Expression | Severity |
|---|---|---|
| Positive transaction value | `valor_transacao > 0` on silver | CRITICAL |
| Non-negative area | `area_construida_m2 >= 0 OR area_construida_m2 IS NULL` | HIGH |
| Valid price/m² | `price_per_m2 > 0 OR price_per_m2 IS NULL` | HIGH |
| Valid proportion | `proporcao_transmitida_pct BETWEEN 0 AND 100 OR proporcao_transmitida_pct IS NULL` | HIGH |
| Sensible construction year | `acc_iptu BETWEEN 1500 AND 2026 OR acc_iptu IS NULL` | MEDIUM |
| Gold transaction count | `transaction_count >= 1` on all gold tables | CRITICAL |
| Non-negative gold median | `kpi_median_price > 0 OR kpi_median_price IS NULL` | HIGH |
| Non-negative gold m² median | `kpi_median_price_per_m2 > 0 OR kpi_median_price_per_m2 IS NULL` | HIGH |

### Freshness Checks (Soda Core — run on Bronze after ingestion)

```yaml
# soda/checks/bronze_itbi_transactions.yml
checks for bronze_itbi_transactions:
  - freshness(ingested_at) < 35d:
      name: monthly_load_freshness
      warn: when > 30d
      fail: when > 35d
  - row_count > 0:
      name: non_empty_table
  - missing_count(sql_cadastro) = 0:
      name: sql_cadastro_not_null
  - missing_count(bairro) = 0:
      name: bairro_not_null
  - missing_count(valor_transacao) = 0:
      name: valor_transacao_not_null
  - missing_count(data_transacao) = 0:
      name: data_transacao_not_null
  - duplicate_count(sql_cadastro, data_transacao, valor_transacao, source_sheet) = 0:
      name: bronze_composite_key_unique
      warn: when > 0
```

### Privacy / Exclusion Enforcement Test

A separate Soda Core check verifies that the two privacy columns were never loaded:

```yaml
# soda/checks/bronze_privacy_guard.yml
checks for bronze_itbi_transactions:
  - schema:
      name: privacy_columns_absent
      fail:
        when required column missing: []
        when forbidden column present:
          - cartorio_de_registro
          - matricula_do_imovel
```

---

## dbt Project Structure

```
dbt_project/
  models/
    bronze/
      bronze_itbi_transactions.sql       # source reference only — Bronze is loaded by Python
      schema.yml                         # Bronze source definition + Soda tests
    silver/
      silver_itbi_transactions.sql       # full Sub-step 1 + Sub-step 2 in one model
      schema.yml
    gold/
      gold_itbi_monthly_summary.sql
      gold_itbi_neighborhood_ranking.sql
      gold_itbi_price_per_m2.sql
      schema.yml
  seeds/
    seed_uso_lookup.csv
    seed_padrao_lookup.csv
  macros/
    normalize_bairro.sql               # bairro normalization macro (accent strip + abbrev expansion)
  tests/
    (custom singular tests if needed)
  dbt_project.yml
  profiles.yml                         # DuckDB path configured here; not committed
```

## Makefile Pipeline Targets

```makefile
# Representative targets — Engineer implements full commands

ingest:        ## Run Python ingestion script (Bronze load)
    .venv/bin/python src/ingest.py --file data/raw/itbi_sp_2026.xlsx

soda-bronze:   ## Run Soda Core DQ checks on Bronze
    .venv/bin/soda scan -d itbi_duckdb -c soda/configuration.yml soda/checks/bronze_itbi_transactions.yml

dbt-run:       ## Run all dbt models (Silver + Gold)
    .venv/bin/dbt run --project-dir dbt_project --profiles-dir dbt_project

dbt-test:      ## Run all dbt tests
    .venv/bin/dbt test --project-dir dbt_project --profiles-dir dbt_project

dbt-seed:      ## Load seed lookup tables
    .venv/bin/dbt seed --project-dir dbt_project --profiles-dir dbt_project

dashboard:     ## Launch Streamlit dashboard
    .venv/bin/streamlit run src/dashboard.py

pipeline: ingest soda-bronze dbt-seed dbt-run dbt-test dashboard
    ## Full pipeline: ingest → DQ → seeds → transform → test → serve
```

All Python tools run inside `.venv/`. The `pipeline` target is the single command to run the full end-to-end flow after dropping a new or updated XLSX file.
