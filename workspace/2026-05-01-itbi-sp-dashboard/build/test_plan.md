# Test Plan
## Request ID: 2026-05-01-itbi-sp-dashboard
## Version: v1.0 — 2026-05-01

---

## 1. Scope

This test plan covers all data quality checks for the ITBI SP Dashboard pipeline across all three medallion layers. Tests are divided by tooling:

- **Soda Core** — Bronze layer checks (run after ingestion, before dbt)
- **dbt tests** — Silver and Gold layer checks (run after `dbt run`)

**Severity definitions:**
- **CRITICAL** — Failure blocks release. Pipeline must not serve the dashboard until resolved.
- **HIGH** — Failure requires Coordinator exception to proceed. Anomaly must be documented.
- **MEDIUM** — Tracked and logged. Does not block release but must be triaged within one sprint.
- **LOW** — Informational only. Logged for audit.

**Layers covered:**
- Bronze: `bronze_itbi_transactions`
- Silver: `silver_itbi_transactions`
- Gold: `gold_itbi_monthly_summary`, `gold_itbi_neighborhood_ranking`, `gold_itbi_price_per_m2`
- Seeds: `seed_uso_lookup`, `seed_padrao_lookup`

---

## 2. Test Table

### 2.1 Bronze Layer — Soda Core Checks

Run via: `make soda-bronze`

| test_name | target | rule | severity | expected_result |
|---|---|---|---|---|
| `non_empty_table` | `bronze_itbi_transactions` | `row_count > 0` | CRITICAL | Table contains at least 1 row after ingestion |
| `min_rows_per_sheet` | `bronze_itbi_transactions` | `row_count > 100` (filter: `source_sheet IS NOT NULL`) | HIGH | Each ingested sheet contributes more than 100 rows; fewer rows indicates truncated source |
| `monthly_load_freshness` | `bronze_itbi_transactions.ingested_at` | `freshness < 35d` (warn > 30d, fail > 35d) | CRITICAL (fail) / HIGH (warn) | Max ingested_at is within 35 days of current date; warns at 30-day threshold |
| `sql_cadastro_not_null` | `bronze_itbi_transactions.sql_cadastro` | `missing_count = 0` | CRITICAL | No NULL values in the primary property identifier |
| `bairro_not_null` | `bronze_itbi_transactions.bairro` | `missing_count = 0` | CRITICAL | No NULL neighborhood values — required for Silver normalization |
| `natureza_transacao_not_null` | `bronze_itbi_transactions.natureza_transacao` | `missing_count = 0` | CRITICAL | No NULL transaction type values |
| `valor_transacao_not_null` | `bronze_itbi_transactions.valor_transacao` | `missing_count = 0` | CRITICAL | No NULL transaction values — required for all financial aggregations |
| `data_transacao_not_null` | `bronze_itbi_transactions.data_transacao` | `missing_count = 0` | CRITICAL | No NULL transaction dates — required for month_year derivation |
| `source_sheet_not_null` | `bronze_itbi_transactions.source_sheet` | `missing_count = 0` | CRITICAL | Every row must carry its sheet origin for traceability |
| `ingested_at_not_null` | `bronze_itbi_transactions.ingested_at` | `missing_count = 0` | CRITICAL | Ingestion timestamp must always be set |
| `bronze_composite_key_unique` | `bronze_itbi_transactions` | `duplicate_count(sql_cadastro, data_transacao, valor_transacao, source_sheet) = 0` | HIGH (warn) | Composite key should be unique per sheet; duplicates may indicate source re-issuance — warns but does not block (Silver handles dedup via surrogate key) |

### 2.2 Bronze Layer — Privacy Guard (Soda Core)

Run via: `make soda-bronze` (privacy guard runs first, before standard checks)

| test_name | target | rule | severity | expected_result |
|---|---|---|---|---|
| `privacy_columns_absent` | `bronze_itbi_transactions` schema | `when forbidden column present: [cartorio_de_registro, matricula_do_imovel]` | CRITICAL | Neither `cartorio_de_registro` nor `matricula_do_imovel` column exists in the table schema — ingestion script must never write them |

### 2.3 Silver Layer — dbt Tests

Run via: `make dbt-test` (after `make dbt-run`)

#### Null Checks

| test_name | target | rule | severity | expected_result |
|---|---|---|---|---|
| `not_null_transaction_id` | `silver_itbi_transactions.transaction_id` | `not_null` | CRITICAL | No NULL surrogate keys — all rows must have a deterministic ID |
| `not_null_sql_cadastro` | `silver_itbi_transactions.sql_cadastro` | `not_null` | CRITICAL | Property ID must always be present |
| `not_null_bairro_raw` | `silver_itbi_transactions.bairro_raw` | `not_null` | CRITICAL | Raw neighborhood preserved from Bronze |
| `not_null_bairro_normalized` | `silver_itbi_transactions.bairro_normalized` | `not_null` | CRITICAL | Normalized neighborhood required for all Gold aggregations |
| `not_null_valor_transacao` | `silver_itbi_transactions.valor_transacao` | `not_null` | CRITICAL | All Silver rows must have a positive transaction value |
| `not_null_data_transacao` | `silver_itbi_transactions.data_transacao` | `not_null` | CRITICAL | Date required for month derivation |
| `not_null_month_year` | `silver_itbi_transactions.month_year` | `not_null` | CRITICAL | Month dimension required for all Gold time grouping |
| `not_null_source_sheet` | `silver_itbi_transactions.source_sheet` | `not_null` | CRITICAL | Lineage traceability |
| `not_null_ingested_at` | `silver_itbi_transactions.ingested_at` | `not_null` | CRITICAL | Bronze metadata must be carried through |
| `not_null_natureza_transacao_codigo` | `silver_itbi_transactions.natureza_transacao_codigo` | `not_null` | HIGH | Parsed transaction type code; NULL may indicate unexpected natureza format |

#### Uniqueness Tests

| test_name | target | rule | severity | expected_result |
|---|---|---|---|---|
| `unique_transaction_id` | `silver_itbi_transactions.transaction_id` | `unique` | CRITICAL | Each transaction_id must appear exactly once — duplicate surrogate keys indicate collision or source duplication error |

#### Referential Integrity Tests

| test_name | target | rule | severity | expected_result |
|---|---|---|---|---|
| `ri_uso_codigo_to_seed` | `silver_itbi_transactions.uso_codigo` → `seed_uso_lookup.uso_codigo` | `relationships` | HIGH | All uso_codigo values that are not NULL should resolve to a known lookup entry; unresolved codes are allowed (LEFT JOIN) but counted — a high count indicates stale seeds |
| `ri_padrao_codigo_to_seed` | `silver_itbi_transactions.padrao_codigo` → `seed_padrao_lookup.padrao_codigo` | `relationships` | HIGH | Same as above for construction standard codes |

#### Business Rule Assertions (dbt_utils.expression_is_true)

| test_name | target | rule | severity | expected_result |
|---|---|---|---|---|
| `positive_valor_transacao` | `silver_itbi_transactions` | `valor_transacao > 0` | CRITICAL | All Silver rows must have positive transaction value — rows with zero or null are filtered in the Silver CTE |
| `non_negative_area_construida` | `silver_itbi_transactions` | `area_construida_m2 >= 0 OR area_construida_m2 IS NULL` | HIGH | Built area cannot be negative; NULL is valid (land-only transactions) |
| `valid_price_per_m2` | `silver_itbi_transactions` | `price_per_m2 > 0 OR price_per_m2 IS NULL` | HIGH | price_per_m2 when present must be positive; NULL allowed when area = 0 or NULL |
| `valid_proporcao_range` | `silver_itbi_transactions` | `proporcao_transmitida_pct BETWEEN 0 AND 100 OR proporcao_transmitida_pct IS NULL` | HIGH | Transfer proportion must be in 0–100 range |
| `valid_acc_iptu_range` | `silver_itbi_transactions` | `acc_iptu BETWEEN 1500 AND 2026 OR acc_iptu IS NULL` | MEDIUM | Year of construction must be plausible (1500–2026); outliers flag source data issues |
| `valid_data_transacao_range` | `silver_itbi_transactions` | `data_transacao >= '2024-01-01'` | MEDIUM | Transactions before 2024 may indicate delayed ITBI registrations — flag but do not exclude |

#### Accepted Values

| test_name | target | rule | severity | expected_result |
|---|---|---|---|---|
| `accepted_natureza_codigo_numeric` | `silver_itbi_transactions.natureza_transacao_codigo` | `accepted_values` — only numeric strings | HIGH | Transaction type code should always be numeric; non-numeric values indicate parse failure or new source format |

### 2.4 Gold Layer — dbt Tests

#### `gold_itbi_monthly_summary`

| test_name | target | rule | severity | expected_result |
|---|---|---|---|---|
| `not_null_monthly_summary_id` | `gold_itbi_monthly_summary.monthly_summary_id` | `not_null` | CRITICAL | PK must never be NULL |
| `unique_monthly_summary_id` | `gold_itbi_monthly_summary.monthly_summary_id` | `unique` | CRITICAL | One row per month — duplicates indicate month_year collision |
| `not_null_month_year` | `gold_itbi_monthly_summary.month_year` | `not_null` | CRITICAL | Time dimension required |
| `not_null_transaction_count` | `gold_itbi_monthly_summary.transaction_count` | `not_null` | CRITICAL | Aggregation count must always be present |
| `positive_transaction_count` | `gold_itbi_monthly_summary` | `transaction_count >= 1` | CRITICAL | Every monthly summary row must represent at least 1 transaction |
| `non_negative_kpi_median_price` | `gold_itbi_monthly_summary` | `kpi_median_price > 0 OR kpi_median_price IS NULL` | HIGH | Median price when present must be positive |
| `non_negative_kpi_median_price_per_m2` | `gold_itbi_monthly_summary` | `kpi_median_price_per_m2 > 0 OR kpi_median_price_per_m2 IS NULL` | HIGH | Median price/m² when present must be positive |

#### `gold_itbi_neighborhood_ranking`

| test_name | target | rule | severity | expected_result |
|---|---|---|---|---|
| `not_null_neighborhood_month_id` | `gold_itbi_neighborhood_ranking.neighborhood_month_id` | `not_null` | CRITICAL | PK must never be NULL |
| `unique_neighborhood_month_id` | `gold_itbi_neighborhood_ranking.neighborhood_month_id` | `unique` | CRITICAL | One row per (bairro, month) combination |
| `not_null_bairro_normalized` | `gold_itbi_neighborhood_ranking.bairro_normalized` | `not_null` | CRITICAL | Neighborhood dimension required |
| `not_null_month_year` | `gold_itbi_neighborhood_ranking.month_year` | `not_null` | CRITICAL | Time dimension required |
| `not_null_transaction_count` | `gold_itbi_neighborhood_ranking.transaction_count` | `not_null` | CRITICAL | Aggregation count must always be present |
| `positive_transaction_count` | `gold_itbi_neighborhood_ranking` | `transaction_count >= 1` | CRITICAL | Each (bairro, month) row must have at least 1 transaction |
| `ri_month_year_to_monthly_summary` | `gold_itbi_neighborhood_ranking.month_year` → `gold_itbi_monthly_summary.month_year` | `relationships` | HIGH | Every neighborhood month must have a corresponding monthly summary — orphan rows indicate aggregation inconsistency |
| `valid_mom_price_change_range` | `gold_itbi_neighborhood_ranking` | `kpi_mom_price_change_pct BETWEEN -100 AND 500 OR kpi_mom_price_change_pct IS NULL` | MEDIUM | MoM price change outside -100%/+500% range likely indicates normalization error; flag for investigation |

#### `gold_itbi_price_per_m2`

| test_name | target | rule | severity | expected_result |
|---|---|---|---|---|
| `not_null_price_m2_id` | `gold_itbi_price_per_m2.price_m2_id` | `not_null` | CRITICAL | PK must never be NULL |
| `unique_price_m2_id` | `gold_itbi_price_per_m2.price_m2_id` | `unique` | CRITICAL | One row per (bairro, uso_desc, month) combination |
| `not_null_bairro_normalized` | `gold_itbi_price_per_m2.bairro_normalized` | `not_null` | CRITICAL | Neighborhood dimension required |
| `not_null_uso_desc` | `gold_itbi_price_per_m2.uso_desc` | `not_null` | CRITICAL | Use type dimension required (COALESCE to 'UNKNOWN' ensures this) |
| `not_null_month_year` | `gold_itbi_price_per_m2.month_year` | `not_null` | CRITICAL | Time dimension required |
| `not_null_transaction_count` | `gold_itbi_price_per_m2.transaction_count` | `not_null` | CRITICAL | Row must represent at least 1 transaction |
| `positive_kpi_median_price_per_m2` | `gold_itbi_price_per_m2` | `kpi_median_price_per_m2 > 0` | CRITICAL | Median price/m² must always be positive in this table (only rows with price_per_m2 IS NOT NULL are included) |
| `ri_month_year_to_monthly_summary` | `gold_itbi_price_per_m2.month_year` → `gold_itbi_monthly_summary.month_year` | `relationships` | HIGH | Every price/m² month must reference a monthly summary |

### 2.5 Seed Tables — dbt Tests

| test_name | target | rule | severity | expected_result |
|---|---|---|---|---|
| `unique_uso_codigo` | `seed_uso_lookup.uso_codigo` | `unique` | CRITICAL | Use code must be unique — duplicates invalidate LEFT JOIN in Silver |
| `not_null_uso_codigo` | `seed_uso_lookup.uso_codigo` | `not_null` | CRITICAL | Every lookup row must have a code |
| `not_null_uso_descricao_canonical` | `seed_uso_lookup.uso_descricao_canonical` | `not_null` | CRITICAL | Every code must have a canonical description |
| `unique_padrao_codigo` | `seed_padrao_lookup.padrao_codigo` | `unique` | CRITICAL | Standard code must be unique |
| `not_null_padrao_codigo` | `seed_padrao_lookup.padrao_codigo` | `not_null` | CRITICAL | Every lookup row must have a code |
| `not_null_padrao_descricao_canonical` | `seed_padrao_lookup.padrao_descricao_canonical` | `not_null` | CRITICAL | Every code must have a canonical description |

---

## 3. Test Categories Summary

| Category | Count | Tool | Layers |
|---|---|---|---|
| Null checks | 28 | Soda Core + dbt not_null | Bronze, Silver, Gold, Seeds |
| Uniqueness | 6 | Soda Core + dbt unique | Bronze (warn), Silver, Gold |
| Referential integrity | 4 | dbt relationships | Silver → Seeds, Gold → Gold |
| Freshness | 1 | Soda Core | Bronze |
| Business rule assertions | 8 | dbt expression_is_true | Silver, Gold |
| Schema / privacy | 1 | Soda Core schema | Bronze |
| Accepted values | 1 | dbt accepted_values | Silver |
| **Total** | **49** | | |

---

## 4. dbt Schema YAML (reference for test configuration)

**`itbi_sp/models/silver/silver_itbi_transactions.yml` (key tests):**

```yaml
version: 2

models:
  - name: silver_itbi_transactions
    description: "Typed, normalized, and deduplicated ITBI transactions. Contract v1.0."
    columns:
      - name: transaction_id
        tests:
          - not_null
          - unique
      - name: sql_cadastro
        tests:
          - not_null
      - name: bairro_raw
        tests:
          - not_null
      - name: bairro_normalized
        tests:
          - not_null
      - name: valor_transacao
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: "valor_transacao > 0"
              severity: error
      - name: data_transacao
        tests:
          - not_null
      - name: month_year
        tests:
          - not_null
      - name: source_sheet
        tests:
          - not_null
      - name: natureza_transacao_codigo
        tests:
          - not_null:
              severity: warn
      - name: area_construida_m2
        tests:
          - dbt_utils.expression_is_true:
              expression: "area_construida_m2 >= 0 OR area_construida_m2 IS NULL"
              severity: warn
      - name: price_per_m2
        tests:
          - dbt_utils.expression_is_true:
              expression: "price_per_m2 > 0 OR price_per_m2 IS NULL"
              severity: warn
      - name: proporcao_transmitida_pct
        tests:
          - dbt_utils.expression_is_true:
              expression: "proporcao_transmitida_pct BETWEEN 0 AND 100 OR proporcao_transmitida_pct IS NULL"
              severity: warn
      - name: uso_codigo
        tests:
          - relationships:
              to: ref('seed_uso_lookup')
              field: uso_codigo
              severity: warn
      - name: padrao_codigo
        tests:
          - relationships:
              to: ref('seed_padrao_lookup')
              field: padrao_codigo
              severity: warn
```

---

## 5. Release Gate: Test Result Severity Matrix

| Severity | Pass condition | Fail action |
|---|---|---|
| CRITICAL | 0 failures | Pipeline halted; dashboard must not be served; root cause must be resolved before re-run |
| HIGH | 0 failures preferred | Requires documented exception from Coordinator; pipeline can proceed with explicit sign-off |
| MEDIUM | Any count | Logged to `logs/`; tracked in backlog; does not block release |
| LOW | Any count | Informational only |

---

## 6. Evidence Section (to be filled at run time)

### 6.1 Soda Core Run Evidence

```
Date/Time (UTC): ______________________
Run by: ______________________
Soda Core version: ______________________
DuckDB version: ______________________

Bronze check results:
  - privacy_columns_absent: [ PASS | FAIL ]
  - non_empty_table: [ PASS | FAIL ]
  - min_rows_per_sheet: [ PASS | WARN | FAIL ] — actual row count: ______
  - monthly_load_freshness: [ PASS | WARN | FAIL ] — max ingested_at: ______
  - sql_cadastro_not_null: [ PASS | FAIL ]
  - bairro_not_null: [ PASS | FAIL ]
  - natureza_transacao_not_null: [ PASS | FAIL ]
  - valor_transacao_not_null: [ PASS | FAIL ]
  - data_transacao_not_null: [ PASS | FAIL ]
  - source_sheet_not_null: [ PASS | FAIL ]
  - ingested_at_not_null: [ PASS | FAIL ]
  - bronze_composite_key_unique: [ PASS | WARN ] — duplicate count: ______

Soda overall status: [ ALL PASS | HAS WARNINGS | HAS FAILURES ]
```

### 6.2 dbt Test Run Evidence

```
Date/Time (UTC): ______________________
dbt version: ______________________
Command: dbt test --project-dir itbi_sp --profiles-dir itbi_sp

Silver tests:
  CRITICAL:
    - unique.transaction_id: [ PASS | FAIL ] — failures: ______
    - not_null.transaction_id: [ PASS | FAIL ]
    - not_null.valor_transacao: [ PASS | FAIL ]
    - not_null.data_transacao: [ PASS | FAIL ]
    - not_null.month_year: [ PASS | FAIL ]
    - not_null.bairro_normalized: [ PASS | FAIL ]
    - expression_is_true.valor_transacao_gt_0: [ PASS | FAIL ] — failures: ______
  HIGH:
    - not_null.natureza_transacao_codigo: [ PASS | WARN ]
    - relationships.uso_codigo: [ PASS | WARN ] — unresolved count: ______
    - relationships.padrao_codigo: [ PASS | WARN ] — unresolved count: ______
    - expression_is_true.area_construida_m2_gte_0: [ PASS | WARN ]
    - expression_is_true.price_per_m2_valid: [ PASS | WARN ]

Gold — monthly_summary:
  CRITICAL:
    - unique.monthly_summary_id: [ PASS | FAIL ]
    - not_null.monthly_summary_id: [ PASS | FAIL ]
    - expression_is_true.transaction_count_gte_1: [ PASS | FAIL ]

Gold — neighborhood_ranking:
  CRITICAL:
    - unique.neighborhood_month_id: [ PASS | FAIL ]
    - not_null.neighborhood_month_id: [ PASS | FAIL ]
  HIGH:
    - relationships.month_year_to_summary: [ PASS | WARN ]

Gold — price_per_m2:
  CRITICAL:
    - unique.price_m2_id: [ PASS | FAIL ]
    - not_null.price_m2_id: [ PASS | FAIL ]
    - expression_is_true.kpi_median_positive: [ PASS | FAIL ]
  HIGH:
    - relationships.month_year_to_summary: [ PASS | WARN ]

Seeds:
    - unique.seed_uso_lookup.uso_codigo: [ PASS | FAIL ]
    - unique.seed_padrao_lookup.padrao_codigo: [ PASS | FAIL ]

dbt test summary:
  Total tests run: ______
  PASS: ______
  WARN: ______
  ERROR: ______
  FAIL: ______

dbt overall status: [ ALL PASS | HAS WARNINGS | HAS ERRORS ]
```

### 6.3 Row Count Sanity Check (to fill at run time)

```
bronze_itbi_transactions total rows: ______
silver_itbi_transactions total rows: ______  (expected: ≤ bronze, filter removes valor_transacao <= 0)
gold_itbi_monthly_summary rows: ______       (expected: one per distinct month_year)
gold_itbi_neighborhood_ranking rows: ______  (expected: one per bairro × month combination)
gold_itbi_price_per_m2 rows: ______          (expected: one per bairro × uso_desc × month with price_per_m2)
seed_uso_lookup rows: ______
seed_padrao_lookup rows: ______
```

---

## 7. Sign-off Section

| Role | Name | Date | Outcome | Notes |
|---|---|---|---|---|
| Data Engineer | | | [ APPROVED | REJECTED ] | |
| Coordinator | | | [ APPROVED | REJECTED ] | |

**Release decision:** [ APPROVED FOR BI HANDOFF | BLOCKED — pending resolution of issues listed below ]

**Open issues (if any):**

```
1. ___________________________________________
2. ___________________________________________
3. ___________________________________________
```

**Approval grants BI Specialist permission to proceed with Streamlit dashboard implementation against Gold tables.**
