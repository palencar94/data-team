# ITBI SP — Data Sources

---

## Source 1: ITBI Transactions XLSX

**File:** `data/GUIAS DE ITBI PAGAS (2).xlsx`
**Format:** Excel workbook, one sheet per month
**Sheet name pattern:** `MMM-YYYY` (e.g., `JAN-2026`, `FEV-2026`) — auto-detected by regex `^[A-Z]{3}-\d{4}$`
**Other sheets:** `EXPLICAÇÕES` (data dictionary), `Tabela de USOS`, `Tabela de PADRÕES` — ignored by ingestion

### Loaded sheets and row counts
| Sheet | Rows ingested |
|-------|--------------|
| JAN-2026 | 14,734 |
| FEV-2026 | 15,364 |
| MAR-2026 | 19,066 |
| **Total** | **49,164** |

### Source columns (Portuguese) → internal field names

| Source header | Internal field | Notes |
|---------------|---------------|-------|
| N° do Cadastro (SQL) | sql_cadastro | Property tax ID |
| Nome do Logradouro | nome_logradouro | Street name |
| Número | numero | Street number |
| Complemento | complemento | Unit/complement |
| Bairro | bairro | Neighborhood — ~41% NULL in source |
| Referência | referencia | Map reference |
| CEP | cep | 7-digit in source (missing leading zero) |
| Natureza de Transação | natureza_transacao | Transaction type code + description |
| Valor de Transação (declarado pelo contribuinte) | valor_transacao | Declared transaction value in BRL |
| Data de Transação | data_transacao | Transaction date |
| Valor Venal de Referência | valor_venal_referencia | Reference property value |
| Proporção Transmitida (%) | proporcao_transmitida_pct | Proportion of property transferred (can exceed 100%) |
| Valor Venal de Referência (proporcional) | valor_venal_proporcional | Proportional reference value |
| Base de Cálculo adotada | base_calculo | Tax calculation base |
| Tipo de Financiamento | tipo_financiamento | Financing type |
| Valor Financiado | valor_financiado | Financed value |
| Situação do SQL | situacao_sql | Property tax status |
| Área do Terreno (m2) | area_terreno_m2 | Land area |
| Testada (m) | testada_m | Frontage |
| Fração Ideal | fracao_ideal | Ideal fraction |
| Área Construída (m2) | area_construida_m2 | Built area |
| Uso (IPTU) | uso_iptu_codigo | Property use code |
| Descrição do uso (IPTU) | uso_iptu_descricao | Property use description |
| Padrão (IPTU) | padrao_iptu_codigo | Construction standard code |
| Descrição do padrão (IPTU) | padrao_iptu_descricao | Construction standard description — missing in FEV-2026 sheet |
| ACC (IPTU) | acc_iptu | Year of construction |

### Privacy exclusions (never ingested)
The following columns are detected and skipped by name during ingestion — they are **never written to the database**:
- `Cartório de Registro`
- `Matrícula do Imóvel`

This is enforced in `scripts/ingest.py` via `PRIVACY_COLUMNS` and verified by the Soda `bronze_privacy_guard.yml` check.

---

## Source 2: CEP Lookup (São Paulo city)

**File:** `data/cep_sp.csv`
**Format:** CSV, 300,850 rows
**Purpose:** Maps individual 8-digit CEPs to neighborhood (bairro) names for São Paulo city
**Used for:** Filling NULL `bairro` values in Silver by joining on CEP

### Schema
| Column | Description |
|--------|-------------|
| cep | 8-digit CEP string (no dash), e.g., `01001000` |
| logradouro | Street name |
| lado | Side (odd/even for streets) |
| bairro | Neighborhood name |
| id_cidade | City ID |
| id_bairro | Neighborhood ID |

### CSV header quirk
The file has **6 columns but only 5 header names**. The last header `id_cidade_id_bairro` covers two columns. The ingestion script (`scripts/load_cep_lookup.py`) uses `pd.read_csv(..., names=[...], skiprows=1)` with 6 explicit column names.

### CEP format mismatch
ITBI source CEPs are **7-digit strings** (leading zero stripped by Excel), e.g., `3423000`.
The lookup uses **8-digit strings**, e.g., `03423000`.
The Silver model uses `LPAD(REGEXP_REPLACE(cep, '[^0-9]', ''), 8, '0')` on the ITBI side to normalize before joining.

---

## Reference Seeds

### `itbi_sp/seeds/seed_uso_lookup.csv`
Maps IPTU use codes to canonical descriptions and categories (e.g., `R1` → `RESIDENCIAL UNIFAMILIAR`, category `RESIDENCIAL`). Extracted from the `Tabela de USOS` sheet. 36 rows.

### `itbi_sp/seeds/seed_padrao_lookup.csv`
Maps IPTU construction standard codes to canonical descriptions and categories. Extracted from `Tabela de PADRÕES`. 32 rows.
