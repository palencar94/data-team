# Data Contract
## Request ID: 2026-05-01-itbi-sp-dashboard

---

## Source Overview

- **Source name:** ITBI SP Transaction Data (Imposto sobre Transmissão de Bens Imóveis — São Paulo)
- **Owner:** Data Team / paulo94.alencar@gmail.com
- **Refresh cadence:** Monthly — one new worksheet tab added per month to the XLSX file; pipeline re-runs on file drop; no code change required for new months
- **Delivery method:** Manual drop of a single XLSX file (`itbi_sp_2026.xlsx`) into the `data/raw/` directory; ingestion via Python + openpyxl; auto-detection of all month sheets at runtime
- **Source format:** Microsoft Excel (.xlsx), multi-sheet workbook; one sheet per calendar month (e.g. JAN-2026, FEV-2026); plus auxiliary sheets LEGENDA, EXPLICAÇÕES, Tabela de USOS, Tabela de PADRÕES
- **Known data characteristics:**
  - Transaction date may reflect delayed ITBI registration (date can precede the nominal month of the sheet by weeks or months — this is normal)
  - `Valor Venal de Referência` is 0 when property is absent from IPTU reference database
  - `Área Construída (m2)` is 0 for pure land transactions
  - `Bairro` is free text with inconsistent abbreviations (JD, V, VL, PQ, etc.)
  - Use code and standard code are numeric references resolved via lookup worksheets

---

## Schema

### Bronze Layer: `bronze_itbi_transactions`
All 26 non-private source columns, ingested verbatim. Types are raw (string/text); no transformation applied. Privacy columns 17 and 18 are **excluded at ingestion** — they never reach DuckDB.

| field_name | source_column | type | nullable | business meaning |
|---|---|---|---|---|
| sql_cadastro | N° do Cadastro (SQL) | VARCHAR | NOT NULL | Unique 11-digit property ID assigned by PMSP; basis for property-level dedup |
| nome_logradouro | Nome do Logradouro | VARCHAR | YES | Street name as recorded in ITBI declaration |
| numero | Número | VARCHAR | YES | Street number; stored as text to preserve leading zeros and ranges |
| complemento | Complemento | VARCHAR | YES | Apartment/unit complement; frequently null |
| bairro | Bairro | VARCHAR | NOT NULL | Neighborhood free-text abbreviation (e.g. JD MORUMBI); requires normalization in Silver |
| referencia | Referência | VARCHAR | YES | Address reference point; often null |
| cep | CEP | VARCHAR | YES | 8-digit postal code; stored as text to preserve leading zero |
| natureza_transacao | Natureza de Transação | VARCHAR | NOT NULL | Transaction type string including numeric prefix (e.g. "4.Arrematação em leilão...") |
| valor_transacao | Valor de Transação (declarado pelo contribuinte) | VARCHAR | NOT NULL | Declared transaction value in BRL; raw string, cast to DECIMAL in Silver |
| data_transacao | Data de Transação | VARCHAR | NOT NULL | Transaction date string; cast to DATE in Silver |
| valor_venal_referencia | Valor Venal de Referência | VARCHAR | YES | PMSP reference market value; 0 means absent from IPTU database |
| proporcao_transmitida_pct | Proporção Transmitida (%) | VARCHAR | YES | Percentage of property transferred (0–100) |
| valor_venal_proporcional | Valor Venal de Referência (proporcional) | VARCHAR | YES | Proportional reference value; may be 0 |
| base_calculo | Base de Cálculo adotada | VARCHAR | YES | Tax base used for ITBI calculation |
| tipo_financiamento | Tipo de Financiamento | VARCHAR | YES | Financing modality; frequently null |
| valor_financiado | Valor Financiado | VARCHAR | YES | Financed portion in BRL; 0 for cash transactions |
| situacao_sql | Situação do SQL | VARCHAR | YES | Property cadastral status (e.g. Ativo Predial) |
| area_terreno_m2 | Área do Terreno (m2) | VARCHAR | YES | Land area in m²; 0 possible for condo units |
| testada_m | Testada (m) | VARCHAR | YES | Street frontage in meters; frequently 0 |
| fracao_ideal | Fração Ideal | VARCHAR | YES | Ideal fraction for condo/split ownership |
| area_construida_m2 | Área Construída (m2) | VARCHAR | YES | Built area in m²; 0 for pure land transactions |
| uso_iptu_codigo | Uso (IPTU) | VARCHAR | YES | Numeric use code; resolved to description via seed_uso_lookup |
| uso_iptu_descricao | Descrição do uso (IPTU) | VARCHAR | YES | Use description as printed in source (may differ from lookup canonical form) |
| padrao_iptu_codigo | Padrão (IPTU) | VARCHAR | YES | Numeric construction standard code; resolved via seed_padrao_lookup |
| padrao_iptu_descricao | Descrição do padrão (IPTU) | VARCHAR | YES | Standard description as printed in source |
| acc_iptu | ACC (IPTU) | VARCHAR | YES | Year of construction per IPTU records |
| source_sheet | (ingestion metadata) | VARCHAR | NOT NULL | Name of the XLSX worksheet tab from which this row was ingested (e.g. "JAN-2026") |
| ingested_at | (ingestion metadata) | TIMESTAMP | NOT NULL | UTC timestamp when the ingestion job wrote this row to DuckDB |

**Excluded columns (never ingested):**
- Column 17: `Cartório de Registro` — registry office name; classified as fiscal/personal secrecy in LEGENDA
- Column 18: `Matrícula do Imóvel` — property registration number; classified as fiscal/personal secrecy in LEGENDA

### Seed Tables (dbt seeds — loaded from XLSX auxiliary sheets)

#### `seed_uso_lookup`
| field_name | type | nullable | business meaning |
|---|---|---|---|
| uso_codigo | VARCHAR | NOT NULL | IPTU use numeric code (PK) |
| uso_descricao_canonical | VARCHAR | NOT NULL | Canonical Portuguese description (normalized, uppercase, no accents) |
| uso_categoria | VARCHAR | YES | Broad category grouping (e.g. RESIDENCIAL, COMERCIAL, INDUSTRIAL) |

#### `seed_padrao_lookup`
| field_name | type | nullable | business meaning |
|---|---|---|---|
| padrao_codigo | VARCHAR | NOT NULL | IPTU construction standard numeric code (PK) |
| padrao_descricao_canonical | VARCHAR | NOT NULL | Canonical Portuguese description (normalized, uppercase, no accents) |
| padrao_categoria | VARCHAR | YES | Broad grouping (e.g. RESIDENCIAL HORIZONTAL, COMERCIAL VERTICAL) |

### Silver Layer: `silver_itbi_transactions`
Typed, deduplicated, standardized, and enriched. One row per transaction after filtering.

| field_name | type | nullable | business meaning |
|---|---|---|---|
| transaction_id | VARCHAR | NOT NULL | Surrogate PK: SHA-256 of (sql_cadastro \|\| data_transacao \|\| valor_transacao \|\| source_sheet) — deterministic and idempotent across re-runs |
| sql_cadastro | VARCHAR | NOT NULL | Property ID carried from Bronze |
| nome_logradouro | VARCHAR | YES | Street name |
| numero | VARCHAR | YES | Street number |
| complemento | VARCHAR | YES | Unit complement |
| bairro_raw | VARCHAR | NOT NULL | Original raw neighborhood string from Bronze (preserved for audit) |
| bairro_normalized | VARCHAR | NOT NULL | Normalized neighborhood: stripped of accents, uppercased, abbreviations expanded (see normalization rules below) |
| referencia | VARCHAR | YES | Address reference |
| cep | VARCHAR | YES | Postal code |
| natureza_transacao_codigo | VARCHAR | NOT NULL | Numeric prefix extracted from natureza string (e.g. "4") |
| natureza_transacao_descricao | VARCHAR | NOT NULL | Remainder description after code prefix removal |
| valor_transacao | DECIMAL(18,2) | NOT NULL | Declared transaction value in BRL; must be > 0 (rows with 0 filtered out) |
| data_transacao | DATE | NOT NULL | Transaction date cast from source string |
| month_year | VARCHAR | NOT NULL | Derived as YYYY-MM string from data_transacao (e.g. "2026-01") |
| valor_venal_referencia | DECIMAL(18,2) | YES | Reference value; 0 in source becomes NULL |
| proporcao_transmitida_pct | DECIMAL(5,2) | YES | Transfer proportion 0–100 |
| valor_venal_proporcional | DECIMAL(18,2) | YES | Proportional reference value; 0 becomes NULL |
| base_calculo | DECIMAL(18,2) | YES | Tax calculation base |
| tipo_financiamento | VARCHAR | YES | Financing type; NULL if blank |
| valor_financiado | DECIMAL(18,2) | YES | Financed amount; 0 preserved (valid for cash) |
| situacao_sql | VARCHAR | YES | Property cadastral status |
| area_terreno_m2 | DECIMAL(12,2) | YES | Land area m²; 0 preserved (valid) |
| testada_m | DECIMAL(10,2) | YES | Street frontage; 0 preserved |
| fracao_ideal | DECIMAL(10,6) | YES | Ideal fraction |
| area_construida_m2 | DECIMAL(12,2) | YES | Built area; 0 preserved in column but excluded from price_per_m2 calc |
| uso_codigo | VARCHAR | YES | IPTU use code |
| uso_desc | VARCHAR | YES | Canonical use description from seed_uso_lookup (fallback: source description) |
| padrao_codigo | VARCHAR | YES | IPTU construction standard code |
| padrao_desc | VARCHAR | YES | Canonical standard description from seed_padrao_lookup (fallback: source description) |
| acc_iptu | INTEGER | YES | Year of construction; NULL if non-numeric in source |
| price_per_m2 | DECIMAL(18,2) | YES | valor_transacao / area_construida_m2; NULL when area_construida_m2 = 0 or NULL |
| source_sheet | VARCHAR | NOT NULL | Source worksheet tab name |
| ingested_at | TIMESTAMP | NOT NULL | Carried from Bronze |
| created_at | TIMESTAMP | NOT NULL | UTC timestamp when this Silver row was written |

### Gold Layer

#### `gold_itbi_monthly_summary`
| field_name | type | nullable | business meaning |
|---|---|---|---|
| monthly_summary_id | VARCHAR | NOT NULL | Surrogate PK: SHA-256 of month_year |
| month_year | VARCHAR | NOT NULL | Calendar month as YYYY-MM |
| transaction_count | INTEGER | NOT NULL | Total qualifying transactions in month |
| total_value_brl | DECIMAL(20,2) | NOT NULL | Sum of all transaction values |
| kpi_median_price | DECIMAL(18,2) | YES | Median declared transaction value (BRL) |
| kpi_median_price_per_m2 | DECIMAL(18,2) | YES | Median price per m² (NULL when insufficient built-area data) |
| avg_price_per_m2 | DECIMAL(18,2) | YES | Mean price per m² (supplementary; use median for reporting) |
| created_at | TIMESTAMP | NOT NULL | Row write timestamp |

#### `gold_itbi_neighborhood_ranking`
| field_name | type | nullable | business meaning |
|---|---|---|---|
| neighborhood_month_id | VARCHAR | NOT NULL | Surrogate PK: SHA-256 of (bairro_normalized \|\| month_year) |
| bairro_normalized | VARCHAR | NOT NULL | Normalized neighborhood name |
| month_year | VARCHAR | NOT NULL | Calendar month as YYYY-MM |
| transaction_count | INTEGER | NOT NULL | Number of transactions in bairro + month |
| kpi_median_price | DECIMAL(18,2) | YES | Median transaction value (BRL) |
| kpi_median_price_per_m2 | DECIMAL(18,2) | YES | Median price per m² |
| kpi_mom_price_change_pct | DECIMAL(10,4) | YES | Month-over-month change in median price (%); NULL for first observed month of bairro |
| kpi_mom_price_per_m2_change_pct | DECIMAL(10,4) | YES | MoM change in median price_per_m2 (%); NULL for first month |
| created_at | TIMESTAMP | NOT NULL | Row write timestamp |

#### `gold_itbi_price_per_m2`
| field_name | type | nullable | business meaning |
|---|---|---|---|
| price_m2_id | VARCHAR | NOT NULL | Surrogate PK: SHA-256 of (bairro_normalized \|\| uso_desc \|\| month_year) |
| bairro_normalized | VARCHAR | NOT NULL | Normalized neighborhood name |
| uso_desc | VARCHAR | NOT NULL | Canonical use description (RESIDENCIAL, COMERCIAL, etc.) |
| month_year | VARCHAR | NOT NULL | Calendar month as YYYY-MM |
| transaction_count | INTEGER | NOT NULL | Transactions with area_construida_m2 > 0 in this segment |
| kpi_median_price_per_m2 | DECIMAL(18,2) | YES | Median price per m² for this bairro + use + month |
| kpi_avg_price_per_m2 | DECIMAL(18,2) | YES | Mean price per m² (supplementary) |
| created_at | TIMESTAMP | NOT NULL | Row write timestamp |

---

## Quality Expectations

### Required (NOT NULL) Fields
**Bronze:** `sql_cadastro`, `bairro`, `natureza_transacao`, `valor_transacao`, `data_transacao`, `source_sheet`, `ingested_at`

**Silver:** `transaction_id`, `sql_cadastro`, `bairro_raw`, `bairro_normalized`, `natureza_transacao_codigo`, `valor_transacao`, `data_transacao`, `month_year`, `source_sheet`, `ingested_at`, `created_at`

**Gold — all tables:** all surrogate key fields, `month_year`, `transaction_count`, `created_at`

### Unique Keys
| Table | Key | Test severity |
|---|---|---|
| bronze_itbi_transactions | (sql_cadastro, data_transacao, valor_transacao, source_sheet) | HIGH — warn on duplicates, do not block |
| silver_itbi_transactions | transaction_id | CRITICAL — blocks release |
| gold_itbi_monthly_summary | monthly_summary_id | CRITICAL |
| gold_itbi_neighborhood_ranking | neighborhood_month_id | CRITICAL |
| gold_itbi_price_per_m2 | price_m2_id | CRITICAL |
| seed_uso_lookup | uso_codigo | CRITICAL |
| seed_padrao_lookup | padrao_codigo | CRITICAL |

### Allowed Values / Ranges
| Field | Rule | Severity |
|---|---|---|
| silver.valor_transacao | > 0 (filter enforced in Silver) | CRITICAL |
| silver.proporcao_transmitida_pct | 0 – 100 | HIGH |
| silver.area_terreno_m2 | >= 0 | HIGH |
| silver.area_construida_m2 | >= 0 | HIGH |
| silver.price_per_m2 | > 0 when not NULL | HIGH |
| silver.acc_iptu | 1500 – 2026 (sanity range) | MEDIUM |
| silver.data_transacao | >= 2024-01-01 (allowing for pre-2026 delayed registrations) | MEDIUM |
| gold.transaction_count | >= 1 | CRITICAL |
| gold.kpi_mom_price_change_pct | accepted range -100 to +500 (outlier flag beyond ±200) | MEDIUM |

### Freshness SLA
| Dataset | Expected cadence | Max staleness | Tier |
|---|---|---|---|
| bronze_itbi_transactions | Monthly file drop + pipeline run | 48 hours after file drop | Tier 2 |
| silver_itbi_transactions | Immediately after Bronze run | +1 hour after Bronze completes | Tier 2 |
| gold_itbi_* | Immediately after Silver run | +1 hour after Silver completes | Tier 2 |

Soda Core freshness check on `bronze_itbi_transactions.ingested_at`: warn if no new rows within 35 days of previous ingestion date (catches missed monthly loads).

---

## Change Policy

### Backward Compatibility
- Adding new month sheets to the XLSX is a non-breaking change — the ingestion script auto-detects all sheets; no pipeline code changes required
- Adding new columns to source sheets is non-breaking — Bronze ingests only the 26 known columns by name; extra source columns are silently ignored
- **Breaking changes** (require coordinator approval + version bump): removal of any of the 26 Bronze columns, rename of existing columns, change in `Uso` or `Padrão` code meaning in lookup sheets

### Versioning Strategy
- This contract is version **v1.0** (initial design, 2026-05-01)
- Contract version is stored as a comment header in each dbt model file
- Breaking changes increment major version; additive changes increment minor version
- Seed lookup tables (`seed_uso_lookup`, `seed_padrao_lookup`) are versioned alongside the contract

### Notification Process
- Schema changes in the upstream XLSX must be flagged by the data owner to paulo94.alencar@gmail.com before the next pipeline run
- Pipeline failures due to schema changes are surfaced in `logs/` and treated as Tier 2 incidents per the SLA Freshness Policy

---

## Security / Governance

### Sensitive Columns
| Column (source) | Reason | Action |
|---|---|---|
| Cartório de Registro (col 17) | Personal/fiscal secrecy per LEGENDA sheet | Excluded at ingestion — never written to DuckDB or any intermediate file |
| Matrícula do Imóvel (col 18) | Personal/fiscal secrecy per LEGENDA sheet | Excluded at ingestion — never written to DuckDB or any intermediate file |

### Masking / Anonymization Rules
- No masking is applied to the 26 retained columns — they are already public ITBI declaration data published by Prefeitura de São Paulo
- The ingestion script must explicitly skip columns by index (17 and 18, 1-based) before writing any row; this must be enforced in code, not filtered after write
- The `sql_cadastro` (property ID) is retained as a technical key for dedup — it is a cadastral reference, not a personal identifier

### Access Restrictions
- The DuckDB file (`itbi_sp.duckdb`) must be stored locally and not committed to version control
- The raw XLSX file must not be committed to version control (add `data/raw/*.xlsx` to `.gitignore`)
- Dashboard access (Streamlit) is local by default; any deployment to a shared environment requires explicit authorization
- Gold tables are the only layer exposed to the Streamlit dashboard; Bronze and Silver are internal pipeline layers
