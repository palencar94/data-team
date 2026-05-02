# ITBI SP — Schema Reference

All tables live in the `main` schema of the DuckDB file at `$DB_PATH`.

---

## silver_itbi_transactions

**Grain:** One row per valid ITBI transaction (valor_transacao > 0, data_transacao NOT NULL)
**Row count:** ~49,162

| Column | Type | Description |
|--------|------|-------------|
| transaction_id | VARCHAR | MD5 surrogate key: md5(sql_cadastro \|\| '\|' \|\| data_transacao \|\| '\|' \|\| valor_transacao \|\| '\|' \|\| source_sheet) |
| sql_cadastro | VARCHAR | Property tax cadastre number (NOT NULL) |
| nome_logradouro | VARCHAR | Street name |
| numero | VARCHAR | Street number |
| complemento | VARCHAR | Unit/complement |
| bairro_raw | VARCHAR | Neighborhood from source — ~41% NULL (WARN, not fail) |
| bairro_from_cep | VARCHAR | Neighborhood resolved via CEP lookup — fills most NULLs |
| bairro_normalized | VARCHAR | Normalized neighborhood: COALESCE(bairro_raw, bairro_from_cep) → macro → DESCONHECIDO fallback. NOT NULL. |
| referencia | VARCHAR | Map reference |
| cep | VARCHAR | CEP as 7-digit string from source (no formatting, no dash) |
| natureza_transacao_codigo | VARCHAR | Transaction type code (extracted from "NN. Description" format) |
| natureza_transacao_descricao | VARCHAR | Transaction type description |
| valor_transacao | DECIMAL(18,2) | Transaction value in BRL. NOT NULL, > 0. |
| data_transacao | DATE | Transaction date. NOT NULL. |
| month_year | VARCHAR | YYYY-MM extracted from data_transacao. NOT NULL. |
| valor_venal_referencia | DECIMAL(18,2) | Reference property value (0 → NULL) |
| proporcao_transmitida_pct | DECIMAL(5,2) | % of property transferred — can exceed 100 (valid for partial transfers) |
| valor_venal_proporcional | DECIMAL(18,2) | Proportional reference value (0 → NULL) |
| base_calculo | DECIMAL(18,2) | Tax calculation base |
| tipo_financiamento | VARCHAR | Financing type |
| valor_financiado | DECIMAL(18,2) | Financed amount |
| situacao_sql | VARCHAR | Property tax status code |
| area_terreno_m2 | DECIMAL(12,2) | Land area in m² |
| testada_m | DECIMAL(10,2) | Frontage in meters |
| fracao_ideal | DECIMAL(10,6) | Ideal fraction of property |
| area_construida_m2 | DECIMAL(12,2) | Built area in m² |
| uso_codigo | VARCHAR | Property use code (key for seed_uso_lookup) |
| uso_desc | VARCHAR | Resolved use description (COALESCE of canonical or source description) |
| uso_categoria | VARCHAR | Use category (from seed, e.g., RESIDENCIAL, COMERCIAL) |
| padrao_codigo | VARCHAR | Construction standard code (key for seed_padrao_lookup) |
| padrao_desc | VARCHAR | Resolved construction standard description |
| padrao_categoria | VARCHAR | Construction standard category |
| acc_iptu | INTEGER | Year of construction |
| price_per_m2 | DECIMAL(18,2) | ROUND(valor_transacao / area_construida_m2, 2) — NULL when area_construida_m2 IS NULL or 0 |
| source_sheet | VARCHAR | Sheet name (e.g., JAN-2026). NOT NULL. |
| ingested_at | TIMESTAMP | UTC timestamp of ingestion. NOT NULL. |
| created_at | TIMESTAMP | dbt model run timestamp |

---

## gold_itbi_monthly_summary

**Grain:** One row per month_year
**Row count:** ~104 months (1995-01 to 2026-04 due to old records in source; main data is 2026-01 to 2026-03)

| Column | Type | Description |
|--------|------|-------------|
| monthly_summary_id | VARCHAR | MD5(month_year). PK. NOT NULL UNIQUE. |
| month_year | VARCHAR | YYYY-MM. NOT NULL. |
| transaction_count | INTEGER | Count of transactions. NOT NULL, ≥ 1. |
| total_value_brl | DECIMAL | Sum of valor_transacao |
| kpi_median_price | DECIMAL | PERCENTILE_CONT(0.5) of valor_transacao |
| kpi_median_price_per_m2 | DECIMAL | PERCENTILE_CONT(0.5) of price_per_m2 (NULL when no area data) |
| avg_price_per_m2 | DECIMAL | AVG of price_per_m2 |
| created_at | TIMESTAMP | Model run timestamp |

---

## gold_itbi_neighborhood_ranking

**Grain:** One row per (bairro_normalized, month_year)
**Row count:** ~7,341

| Column | Type | Description |
|--------|------|-------------|
| neighborhood_month_id | VARCHAR | MD5(bairro_normalized \|\| '\|' \|\| month_year). PK. NOT NULL UNIQUE. |
| bairro_normalized | VARCHAR | Normalized neighborhood name. NOT NULL. |
| month_year | VARCHAR | YYYY-MM. NOT NULL. |
| transaction_count | INTEGER | Count in this neighborhood × month. ≥ 1. |
| kpi_median_price | DECIMAL | Median transaction value in BRL |
| kpi_median_price_per_m2 | DECIMAL | Median price per m² |
| kpi_mom_price_change_pct | DECIMAL | MoM % change in median price (NULL for first month of each neighborhood) |
| kpi_mom_price_per_m2_change_pct | DECIMAL | MoM % change in median price/m² |
| created_at | TIMESTAMP | Model run timestamp |

---

## gold_itbi_price_per_m2

**Grain:** One row per (bairro_normalized, uso_desc, month_year) — only where price_per_m2 is available
**Row count:** ~9,498

| Column | Type | Description |
|--------|------|-------------|
| price_m2_id | VARCHAR | MD5(bairro_normalized \|\| '\|' \|\| uso_desc \|\| '\|' \|\| month_year). PK. NOT NULL UNIQUE. |
| bairro_normalized | VARCHAR | Normalized neighborhood name. NOT NULL. |
| uso_desc | VARCHAR | Resolved use description. NOT NULL. 'UNKNOWN' when unresolved. |
| month_year | VARCHAR | YYYY-MM. NOT NULL. |
| transaction_count | INTEGER | Count with price_per_m2 in this grain |
| kpi_median_price_per_m2 | DECIMAL | Median price per m². Should be > 0 (warn if not). |
| kpi_avg_price_per_m2 | DECIMAL | Average price per m² |
| created_at | TIMESTAMP | Model run timestamp |

---

## seed_uso_lookup

| Column | Type | Description |
|--------|------|-------------|
| uso_codigo | VARCHAR | IPTU use code (e.g., R1, C2) — force VARCHAR, not numeric |
| uso_descricao_canonical | VARCHAR | Canonical description |
| uso_categoria | VARCHAR | Category (RESIDENCIAL, COMERCIAL, INDUSTRIAL, etc.) |

## seed_padrao_lookup

| Column | Type | Description |
|--------|------|-------------|
| padrao_codigo | VARCHAR | IPTU construction standard code — force VARCHAR |
| padrao_descricao_canonical | VARCHAR | Canonical description |
| padrao_categoria | VARCHAR | Category |

---

## raw_cep_lookup

| Column | Type | Description |
|--------|------|-------------|
| cep | VARCHAR | 8-digit CEP string (no dash) |
| logradouro | VARCHAR | Street name |
| lado | VARCHAR | Side (odd/even for street ranges) |
| bairro | VARCHAR | Neighborhood name |
| id_cidade | VARCHAR | City ID |
| id_bairro | VARCHAR | Neighborhood ID |
