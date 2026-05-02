# Pipeline Specification
## Request ID: 2026-05-01-itbi-sp-dashboard
## Version: v1.0 — 2026-05-01

---

## 1. Pipeline Name

**ITBI SP Dashboard Pipeline**

End-to-end pipeline that ingests monthly São Paulo ITBI (Imposto sobre Transmissão de Bens Imóveis) transaction data from a multi-sheet XLSX workbook into DuckDB, transforms it through Bronze → Silver → Gold medallion layers via dbt, validates data quality with Soda Core and dbt tests, and serves a Streamlit analysis dashboard.

---

## 2. Inputs

| Input | Location | Format | Description |
|---|---|---|---|
| ITBI XLSX workbook | `data/raw/itbi_sp_2026.xlsx` | `.xlsx` (multi-sheet) | Primary source — one tab per month (e.g. JAN-2026). New months auto-detected at runtime. |
| seed_uso_lookup | `itbi_sp/seeds/seed_uso_lookup.csv` | CSV | IPTU use code → canonical description lookup (derived from "Tabela de USOS" sheet) |
| seed_padrao_lookup | `itbi_sp/seeds/seed_padrao_lookup.csv` | CSV | IPTU construction standard code → canonical description lookup (from "Tabela de PADRÕES" sheet) |
| `.env` file | `.env` (project root) | Key=Value | `DB_PATH` — path to DuckDB file; never committed to git |

**Sheet detection regex:** `^[A-Z]{3}-\d{4}$` — matches JAN-2026, FEV-2026, MAR-2026, etc. Sheets named LEGENDA, EXPLICAÇÕES, Tabela de USOS, and Tabela de PADRÕES are excluded from transaction ingestion.

**Privacy exclusion (CRITICAL):** Columns named `Cartório de Registro` and `Matrícula do Imóvel` are **never read** — excluded by column name at ingestion before any row is written to DuckDB.

---

## 3. Outputs

| Output | Location | Description |
|---|---|---|
| `bronze_itbi_transactions` | DuckDB table | Raw VARCHAR columns + source_sheet + ingested_at; one row per source row |
| `silver_itbi_transactions` | DuckDB table | Typed, normalized, deduplicated transactions; one row per unique qualifying transaction |
| `gold_itbi_monthly_summary` | DuckDB table | Monthly aggregates — transaction counts, total value, median price, median price/m² |
| `gold_itbi_neighborhood_ranking` | DuckDB table | Per-bairro per-month aggregates with MoM change KPIs |
| `gold_itbi_price_per_m2` | DuckDB table | Per-bairro per-use-type per-month price/m² aggregates |
| `seed_uso_lookup` | DuckDB table | Use code dimension |
| `seed_padrao_lookup` | DuckDB table | Construction standard dimension |
| Ingestion log | `logs/ingestion_<timestamp>.log` | Row counts per sheet, errors, timestamps |
| Soda Core report | stdout / Soda Cloud (optional) | Bronze DQ check results after ingestion |
| dbt test results | stdout / `target/` | Silver + Gold DQ test results |
| Streamlit dashboard | `http://localhost:8501` | Interactive visualization over Gold tables |

**DuckDB file path:** Resolved from `DB_PATH` env variable (`.env`). Default: `workspace/2026-05-01-itbi-sp-dashboard/build/itbi_sp.duckdb`. Not committed to git.

---

## 4. Execution

| Attribute | Value |
|---|---|
| Frequency | Manual trigger on each monthly XLSX file drop — no daemon, no cron |
| Orchestrator | GNU Make (`Makefile`) |
| Full pipeline command | `make pipeline` |
| Individual targets | `make ingest`, `make soda-bronze`, `make dbt-seed`, `make dbt-run`, `make dbt-test`, `make serve` |
| Execution order | ingest → soda-bronze → dbt-seed → dbt-run → dbt-test → serve |
| Python runtime | Python 3.11.x inside `.venv` — no global installs |
| DuckDB version | >= 0.10.x |
| dbt adapter | dbt-duckdb >= 1.7.0 |

### Dependency Graph

```
XLSX file drop
      │
      ▼
make ingest        # Python + openpyxl → DuckDB bronze_itbi_transactions
      │
      ▼
make soda-bronze   # Soda Core DQ checks on Bronze
      │
      ▼
make dbt-seed      # Load seed_uso_lookup + seed_padrao_lookup
      │
      ▼
make dbt-run       # dbt: Silver (from Bronze) → Gold (from Silver)
      │
      ▼
make dbt-test      # dbt tests: not_null, unique, RI, business rules
      │
      ▼
make serve         # Streamlit dashboard on Gold tables
```

---

## 5. Transform Steps

### Step 0 — Ingestion (Python `scripts/ingest.py`)

**Purpose:** Load XLSX tabs into `bronze_itbi_transactions` with idempotency.

**Algorithm:**
1. Load `.env` for `DB_PATH`; open DuckDB connection in read-write mode
2. Open XLSX workbook with `openpyxl` (data_only=True, UTF-8 safe — no CSV intermediary)
3. Enumerate sheet names; filter by regex `^[A-Z]{3}-\d{4}$`
4. For each matching sheet:
   a. Read header row; identify column positions by **name** (not index)
   b. Build allowed column set: the 26 retained fields; skip `Cartório de Registro` and `Matrícula do Imóvel` by name — never read their cell values
   c. Execute `DELETE FROM bronze_itbi_transactions WHERE source_sheet = '<sheet_name>'` (idempotency — allows sheet correction)
   d. Iterate data rows; for each row: strip whitespace from strings, represent empty cells as NULL
   e. Append `source_sheet = sheet_name` and `ingested_at = datetime.utcnow()` to each record
   f. Bulk-insert rows using `duckdb.executemany()` with parameterized INSERT
   g. Log row count to `logs/ingestion_<timestamp>.log`
5. Close connection; exit with code 0 on success, 1 on any unhandled exception

**Complete Python script (`scripts/ingest.py`):**

```python
#!/usr/bin/env python3
"""
ITBI SP — Bronze ingestion script
Loads monthly XLSX sheets into DuckDB bronze_itbi_transactions.
Contract version: v1.0 (2026-05-01)

Privacy guarantee: columns 'Cartório de Registro' and 'Matrícula do Imóvel'
are excluded by name before any row is written to DuckDB.
"""

import re
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import openpyxl
from dotenv import load_dotenv
import os

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SHEET_PATTERN = re.compile(r'^[A-Z]{3}-\d{4}$')

RETAINED_COLUMNS = [
    "sql_cadastro",
    "nome_logradouro",
    "numero",
    "complemento",
    "bairro",
    "referencia",
    "cep",
    "natureza_transacao",
    "valor_transacao",
    "data_transacao",
    "valor_venal_referencia",
    "proporcao_transmitida_pct",
    "valor_venal_proporcional",
    "base_calculo",
    "tipo_financiamento",
    "valor_financiado",
    "situacao_sql",
    "area_terreno_m2",
    "testada_m",
    "fracao_ideal",
    "area_construida_m2",
    "uso_iptu_codigo",
    "uso_iptu_descricao",
    "padrao_iptu_codigo",
    "padrao_iptu_descricao",
    "acc_iptu",
]

# Map from source Excel header names to internal field names
SOURCE_TO_FIELD = {
    "N° do Cadastro (SQL)":                      "sql_cadastro",
    "Nome do Logradouro":                         "nome_logradouro",
    "Número":                                     "numero",
    "Complemento":                                "complemento",
    "Bairro":                                     "bairro",
    "Referência":                                 "referencia",
    "CEP":                                        "cep",
    "Natureza de Transação":                      "natureza_transacao",
    "Valor de Transação (declarado pelo contribuinte)": "valor_transacao",
    "Data de Transação":                          "data_transacao",
    "Valor Venal de Referência":                  "valor_venal_referencia",
    "Proporção Transmitida (%)":                  "proporcao_transmitida_pct",
    "Valor Venal de Referência (proporcional)":   "valor_venal_proporcional",
    "Base de Cálculo adotada":                    "base_calculo",
    "Tipo de Financiamento":                      "tipo_financiamento",
    "Valor Financiado":                           "valor_financiado",
    "Situação do SQL":                            "situacao_sql",
    "Área do Terreno (m2)":                       "area_terreno_m2",
    "Testada (m)":                                "testada_m",
    "Fração Ideal":                               "fracao_ideal",
    "Área Construída (m2)":                       "area_construida_m2",
    "Uso (IPTU)":                                 "uso_iptu_codigo",
    "Descrição do uso (IPTU)":                    "uso_iptu_descricao",
    "Padrão (IPTU)":                              "padrao_iptu_codigo",
    "Descrição do padrão (IPTU)":                "padrao_iptu_descricao",
    "ACC (IPTU)":                                 "acc_iptu",
    # EXCLUDED — never read:
    # "Cartório de Registro"   → excluded
    # "Matrícula do Imóvel"    → excluded
}

PRIVACY_COLUMNS = {"Cartório de Registro", "Matrícula do Imóvel"}

BRONZE_TABLE = "bronze_itbi_transactions"

CREATE_BRONZE_DDL = f"""
CREATE TABLE IF NOT EXISTS {BRONZE_TABLE} (
    sql_cadastro              VARCHAR,
    nome_logradouro           VARCHAR,
    numero                    VARCHAR,
    complemento               VARCHAR,
    bairro                    VARCHAR,
    referencia                VARCHAR,
    cep                       VARCHAR,
    natureza_transacao        VARCHAR,
    valor_transacao           VARCHAR,
    data_transacao            VARCHAR,
    valor_venal_referencia    VARCHAR,
    proporcao_transmitida_pct VARCHAR,
    valor_venal_proporcional  VARCHAR,
    base_calculo              VARCHAR,
    tipo_financiamento        VARCHAR,
    valor_financiado          VARCHAR,
    situacao_sql              VARCHAR,
    area_terreno_m2           VARCHAR,
    testada_m                 VARCHAR,
    fracao_ideal              VARCHAR,
    area_construida_m2        VARCHAR,
    uso_iptu_codigo           VARCHAR,
    uso_iptu_descricao        VARCHAR,
    padrao_iptu_codigo        VARCHAR,
    padrao_iptu_descricao     VARCHAR,
    acc_iptu                  VARCHAR,
    source_sheet              VARCHAR NOT NULL,
    ingested_at               TIMESTAMP NOT NULL
);
"""

INSERT_SQL = f"""
INSERT INTO {BRONZE_TABLE} (
    sql_cadastro, nome_logradouro, numero, complemento, bairro,
    referencia, cep, natureza_transacao, valor_transacao, data_transacao,
    valor_venal_referencia, proporcao_transmitida_pct, valor_venal_proporcional,
    base_calculo, tipo_financiamento, valor_financiado, situacao_sql,
    area_terreno_m2, testada_m, fracao_ideal, area_construida_m2,
    uso_iptu_codigo, uso_iptu_descricao, padrao_iptu_codigo, padrao_iptu_descricao,
    acc_iptu, source_sheet, ingested_at
) VALUES (
    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?, ?, ?, ?
)
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_file = log_dir / f"ingestion_{ts}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file),
        ],
    )
    logger = logging.getLogger("ingest")
    logger.info(f"Log file: {log_file}")
    return logger


def clean_value(val) -> str | None:
    """Strip whitespace; convert empty/None to NULL."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


# ---------------------------------------------------------------------------
# Core ingestion logic
# ---------------------------------------------------------------------------

def ingest_sheet(
    ws,
    sheet_name: str,
    con: duckdb.DuckDBPyConnection,
    ingested_at: datetime,
    logger: logging.Logger,
) -> int:
    """Ingest one worksheet. Returns row count inserted."""

    # Read header row (row 1)
    headers = []
    for cell in next(ws.iter_rows(min_row=1, max_row=1)):
        headers.append(cell.value)

    # Build column index map: field_name → col index (0-based)
    col_index: dict[str, int] = {}
    for idx, header in enumerate(headers):
        if header in PRIVACY_COLUMNS:
            logger.info(
                f"  [PRIVACY] Column '{header}' detected in sheet {sheet_name} — SKIPPED (never read)"
            )
            continue
        field = SOURCE_TO_FIELD.get(header)
        if field:
            col_index[field] = idx

    # Verify all required retained columns are present
    missing = [f for f in RETAINED_COLUMNS if f not in col_index]
    if missing:
        logger.warning(
            f"  [WARN] Sheet {sheet_name}: missing source columns: {missing}. "
            "They will be NULL in Bronze."
        )

    # Delete existing rows for this sheet (idempotency)
    deleted = con.execute(
        f"DELETE FROM {BRONZE_TABLE} WHERE source_sheet = ?", [sheet_name]
    ).fetchone()[0]
    if deleted > 0:
        logger.info(f"  Deleted {deleted} existing rows for sheet '{sheet_name}' (re-ingestion)")

    # Read data rows
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        # Skip completely empty rows
        if all(v is None for v in row):
            continue

        record = []
        for field in RETAINED_COLUMNS:
            idx = col_index.get(field)
            val = clean_value(row[idx]) if idx is not None else None
            record.append(val)

        record.append(sheet_name)           # source_sheet
        record.append(ingested_at)          # ingested_at

        rows.append(tuple(record))

    if rows:
        con.executemany(INSERT_SQL, rows)
    logger.info(f"  Inserted {len(rows)} rows for sheet '{sheet_name}'")
    return len(rows)


def run_ingestion(xlsx_path: str, db_path: str, logger: logging.Logger) -> None:
    logger.info(f"Opening workbook: {xlsx_path}")
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)

    matching_sheets = [s for s in wb.sheetnames if SHEET_PATTERN.match(s)]
    if not matching_sheets:
        logger.error(f"No sheets matching {SHEET_PATTERN.pattern} found in workbook. Aborting.")
        sys.exit(1)
    logger.info(f"Sheets to ingest: {matching_sheets}")

    con = duckdb.connect(db_path)
    con.execute(CREATE_BRONZE_DDL)

    ingested_at = datetime.now(timezone.utc)
    total_rows = 0

    for sheet_name in matching_sheets:
        logger.info(f"Processing sheet: {sheet_name}")
        ws = wb[sheet_name]
        count = ingest_sheet(ws, sheet_name, con, ingested_at, logger)
        total_rows += count

    con.close()
    wb.close()
    logger.info(f"Ingestion complete. Total rows inserted: {total_rows}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    load_dotenv()

    logger = setup_logging()

    parser = argparse.ArgumentParser(description="ITBI SP Bronze ingestion")
    parser.add_argument(
        "--file",
        default="data/raw/itbi_sp_2026.xlsx",
        help="Path to the ITBI XLSX workbook",
    )
    args = parser.parse_args()

    db_path = os.environ.get("DB_PATH")
    if not db_path:
        logger.error("DB_PATH environment variable is not set. Create a .env file.")
        sys.exit(1)

    xlsx_path = args.file
    if not Path(xlsx_path).exists():
        logger.error(f"XLSX file not found: {xlsx_path}")
        sys.exit(1)

    run_ingestion(xlsx_path, db_path, logger)
```

---

### Step 1 — Soda Core DQ Checks on Bronze (`make soda-bronze`)

Run immediately after ingestion, before any dbt transforms. Blocks pipeline on CRITICAL failures.

**Complete Soda Core check files:**

**`itbi_sp/soda/checks/bronze_itbi_transactions.yml`:**
```yaml
# Soda Core checks — Bronze layer
# Contract version: v1.0 (2026-05-01)
# Severity mapping: fail = CRITICAL (blocks pipeline), warn = HIGH (alert, do not block)

checks for bronze_itbi_transactions:

  # Freshness — Tier 2 SLA: 48h after file drop; warn at 30d, fail at 35d
  - freshness(ingested_at) < 35d:
      name: monthly_load_freshness
      warn: when > 30d
      fail: when > 35d

  # Table must not be empty
  - row_count > 0:
      name: non_empty_table

  # Per-sheet row count sanity floor
  # Note: Run this check per-sheet by parameterizing in CI or via filter
  - row_count > 100:
      name: min_rows_per_sheet
      filter: source_sheet IS NOT NULL

  # Required field null checks (CRITICAL)
  - missing_count(sql_cadastro) = 0:
      name: sql_cadastro_not_null
  - missing_count(bairro) = 0:
      name: bairro_not_null
  - missing_count(natureza_transacao) = 0:
      name: natureza_transacao_not_null
  - missing_count(valor_transacao) = 0:
      name: valor_transacao_not_null
  - missing_count(data_transacao) = 0:
      name: data_transacao_not_null
  - missing_count(source_sheet) = 0:
      name: source_sheet_not_null
  - missing_count(ingested_at) = 0:
      name: ingested_at_not_null

  # Composite key uniqueness (HIGH — warn, do not block; Bronze allows duplicates until Silver dedup)
  - duplicate_count(sql_cadastro, data_transacao, valor_transacao, source_sheet) = 0:
      name: bronze_composite_key_unique
      warn: when > 0
```

**`itbi_sp/soda/checks/bronze_privacy_guard.yml`:**
```yaml
# Soda Core privacy guard — verifies that sensitive columns were NEVER loaded
# Contract version: v1.0 (2026-05-01)
# This check FAILS (CRITICAL) if either privacy column is present in the schema.
# Run after every ingestion and after any schema change.

checks for bronze_itbi_transactions:
  - schema:
      name: privacy_columns_absent
      fail:
        when required column missing: []
        when forbidden column present:
          - cartorio_de_registro
          - matricula_do_imovel
```

**`itbi_sp/soda/configuration.yml`:**
```yaml
# Soda Core data source configuration
# DB_PATH is resolved from environment (.env)

data_sources:
  itbi_duckdb:
    type: duckdb
    path: ${DB_PATH}
```

---

### Step 2 — Load Seed Tables (`make dbt-seed`)

Loads `seed_uso_lookup.csv` and `seed_padrao_lookup.csv` into DuckDB via `dbt seed`. Seeds are re-loaded on each run (idempotent — dbt truncates and reloads seeds by default).

**`itbi_sp/seeds/seed_uso_lookup.csv` (example rows — fill from "Tabela de USOS" sheet):**
```csv
uso_codigo,uso_descricao_canonical,uso_categoria
1,RESIDENCIAL UNIFAMILIAR,RESIDENCIAL
2,RESIDENCIAL MULTIFAMILIAR,RESIDENCIAL
3,COMERCIAL,COMERCIAL
4,INDUSTRIAL,INDUSTRIAL
5,INSTITUCIONAL,INSTITUCIONAL
6,MISTO RESIDENCIAL COMERCIAL,MISTO
```

**`itbi_sp/seeds/seed_padrao_lookup.csv` (example rows — fill from "Tabela de PADRÕES" sheet):**
```csv
padrao_codigo,padrao_descricao_canonical,padrao_categoria
1,SIMPLES,RESIDENCIAL HORIZONTAL
2,MEDIO,RESIDENCIAL HORIZONTAL
3,FINO,RESIDENCIAL HORIZONTAL
4,LUXO,RESIDENCIAL HORIZONTAL
5,SIMPLES,RESIDENCIAL VERTICAL
6,MEDIO,RESIDENCIAL VERTICAL
7,FINO,RESIDENCIAL VERTICAL
8,LUXO,RESIDENCIAL VERTICAL
```

---

### Step 3 — Silver Transform (`itbi_sp/models/silver/silver_itbi_transactions.sql`)

**Purpose:** Type all Bronze VARCHAR columns, parse/normalize fields, deduplicate via surrogate key, standardize neighborhood names, resolve use/standard codes, derive `price_per_m2`.

**Materialization:** `table` (full refresh on every run).

**Complete `normalize_bairro` macro (`itbi_sp/macros/normalize_bairro.sql`):**
```sql
{% macro normalize_bairro(col) %}
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    TRIM(REGEXP_REPLACE(
    UPPER(
        -- Strip accents (DuckDB has no unaccent; explicit REPLACE chain)
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            {{ col }},
        'ã','a'),'â','a'),'à','a'),'á','a'),'ä','a'),
        'ê','e'),'é','e'),'è','e'),'ë','e'),
        'í','i'),'ì','i'),'ï','i'),
        'õ','o'),'ô','o'),'ó','o'),'ò','o'),'ö','o'),
        'ú','u'),'ù','u'),'ü','u'),
        'ç','c'),
        'Ã','A'),'Â','A'),'Á','A'),'À','A'),
        'Ê','E'),'É','E'),
        'Í','I'),
        'Õ','O'),'Ô','O'),'Ó','O')
    )
    ), '\s+', ' '))   -- collapse multiple spaces + trim
    , '\bCJTO\b', 'CONJUNTO')
    , '\bCONJ\b', 'CONJUNTO')
    , '\bNCL\b', 'NUCLEO')
    , '\bST\b', 'SETOR')
    , '\bLT\b', 'LOTEAMENTO')
    , '\bCHAC\b', 'CHACARA')
    , '\bCH\b', 'CHACARA')
    , '\bPQE\b', 'PARQUE')
    , '\bPQ\b', 'PARQUE')
    , '\bJARD\b', 'JARDIM')
    , '\bJD\b', 'JARDIM')
    , '\bVL\b', 'VILA')
    , '\bV\b', 'VILA')
    , '\bJARDIM\b', 'JARDIM')  -- idempotent guard
{% endmacro %}
```

**Complete Silver model SQL (`itbi_sp/models/silver/silver_itbi_transactions.sql`):**
```sql
-- silver_itbi_transactions.sql
-- Contract version: v1.0 (2026-05-01)
-- Materialization: table (full refresh)
-- Two logical sub-steps implemented as CTEs in a single model.

{{ config(materialized='table') }}

WITH

-- ===========================================================================
-- Sub-step 1: Typing, Parsing, and Cleaning
-- Source: bronze_itbi_transactions (all columns VARCHAR)
-- ===========================================================================
typed AS (
    SELECT
        -- Identity
        sql_cadastro,
        nome_logradouro,
        numero,
        complemento,
        bairro                                                      AS bairro_raw,
        referencia,
        cep,

        -- Transaction type parsing
        REGEXP_EXTRACT(natureza_transacao, '^([0-9]+)\.', 1)        AS natureza_transacao_codigo,
        REGEXP_REPLACE(natureza_transacao, '^[0-9]+\.\s*', '')      AS natureza_transacao_descricao,

        -- Core financials (TRY_CAST — NULL on parse failure)
        TRY_CAST(valor_transacao AS DECIMAL(18,2))                  AS valor_transacao,
        TRY_CAST(data_transacao AS DATE)                            AS data_transacao,

        -- Reference values (0 → NULL for reporting clarity)
        CASE
            WHEN TRY_CAST(valor_venal_referencia AS DECIMAL(18,2)) = 0 THEN NULL
            ELSE TRY_CAST(valor_venal_referencia AS DECIMAL(18,2))
        END                                                         AS valor_venal_referencia,

        TRY_CAST(proporcao_transmitida_pct AS DECIMAL(5,2))        AS proporcao_transmitida_pct,

        CASE
            WHEN TRY_CAST(valor_venal_proporcional AS DECIMAL(18,2)) = 0 THEN NULL
            ELSE TRY_CAST(valor_venal_proporcional AS DECIMAL(18,2))
        END                                                         AS valor_venal_proporcional,

        TRY_CAST(base_calculo AS DECIMAL(18,2))                    AS base_calculo,
        tipo_financiamento,
        TRY_CAST(valor_financiado AS DECIMAL(18,2))                AS valor_financiado,
        situacao_sql,

        -- Area fields
        TRY_CAST(area_terreno_m2 AS DECIMAL(12,2))                 AS area_terreno_m2,
        TRY_CAST(testada_m AS DECIMAL(10,2))                       AS testada_m,
        TRY_CAST(fracao_ideal AS DECIMAL(10,6))                    AS fracao_ideal,
        TRY_CAST(area_construida_m2 AS DECIMAL(12,2))              AS area_construida_m2,

        -- Use and standard codes (kept as VARCHAR for JOIN)
        uso_iptu_codigo                                             AS uso_codigo,
        uso_iptu_descricao,
        padrao_iptu_codigo                                          AS padrao_codigo,
        padrao_iptu_descricao,

        -- Year of construction
        TRY_CAST(acc_iptu AS INTEGER)                              AS acc_iptu,

        -- Metadata
        source_sheet,
        ingested_at

    FROM {{ ref('bronze_itbi_transactions') }}

    -- Filter: remove rows with no valid positive transaction value
    WHERE TRY_CAST(valor_transacao AS DECIMAL(18,2)) IS NOT NULL
      AND TRY_CAST(valor_transacao AS DECIMAL(18,2)) > 0
),

-- Derive month_year after typing (requires valid data_transacao)
typed_with_month AS (
    SELECT
        *,
        STRFTIME(data_transacao, '%Y-%m')                           AS month_year
    FROM typed
    WHERE data_transacao IS NOT NULL
),

-- ===========================================================================
-- Sub-step 2: Standardization, Enrichment, and Surrogate Key
-- ===========================================================================

-- 2a. Neighborhood normalization via macro
normalized AS (
    SELECT
        *,
        {{ normalize_bairro('bairro_raw') }}                        AS bairro_normalized
    FROM typed_with_month
),

-- 2b. Use code resolution (LEFT JOIN — unresolved codes fall back to source description)
uso_resolved AS (
    SELECT
        n.*,
        COALESCE(u.uso_descricao_canonical, n.uso_iptu_descricao)   AS uso_desc,
        u.uso_categoria
    FROM normalized n
    LEFT JOIN {{ ref('seed_uso_lookup') }} u
        ON n.uso_codigo = u.uso_codigo
),

-- 2c. Construction standard code resolution
padrao_resolved AS (
    SELECT
        u.*,
        COALESCE(p.padrao_descricao_canonical, u.padrao_iptu_descricao) AS padrao_desc,
        p.padrao_categoria
    FROM uso_resolved u
    LEFT JOIN {{ ref('seed_padrao_lookup') }} p
        ON u.padrao_codigo = p.padrao_codigo
),

-- 2d. Derived price_per_m2 (null-safe) + surrogate transaction_id
enriched AS (
    SELECT
        -- Surrogate key (deterministic, idempotent across re-runs)
        md5(
            COALESCE(sql_cadastro, '') || '|' ||
            CAST(data_transacao AS VARCHAR) || '|' ||
            CAST(valor_transacao AS VARCHAR) || '|' ||
            COALESCE(source_sheet, '')
        )                                                           AS transaction_id,

        -- Core identity
        sql_cadastro,
        nome_logradouro,
        numero,
        complemento,
        bairro_raw,
        bairro_normalized,
        referencia,
        cep,

        -- Transaction type
        natureza_transacao_codigo,
        natureza_transacao_descricao,

        -- Financials
        valor_transacao,
        data_transacao,
        month_year,
        valor_venal_referencia,
        proporcao_transmitida_pct,
        valor_venal_proporcional,
        base_calculo,
        tipo_financiamento,
        valor_financiado,

        -- Property attributes
        situacao_sql,
        area_terreno_m2,
        testada_m,
        fracao_ideal,
        area_construida_m2,

        -- Use type (resolved)
        uso_codigo,
        uso_desc,
        uso_categoria,

        -- Construction standard (resolved)
        padrao_codigo,
        padrao_desc,
        padrao_categoria,

        -- Year of construction
        acc_iptu,

        -- Derived KPI
        CASE
            WHEN area_construida_m2 IS NULL OR area_construida_m2 = 0 THEN NULL
            ELSE ROUND(valor_transacao / area_construida_m2, 2)
        END                                                         AS price_per_m2,

        -- Lineage metadata
        source_sheet,
        ingested_at,
        CURRENT_TIMESTAMP                                           AS created_at

    FROM padrao_resolved
)

SELECT * FROM enriched
```

---

### Step 4 — Gold Models (`make dbt-run` continues)

All Gold models: `materialized: table`, full refresh. Source: `silver_itbi_transactions` only.

**`itbi_sp/models/gold/gold_itbi_monthly_summary.sql`:**
```sql
-- gold_itbi_monthly_summary.sql
-- Contract version: v1.0 (2026-05-01)
-- Grain: one row per calendar month (YYYY-MM)
-- Feeds: Chart 1 — Month-over-month price evolution

{{ config(materialized='table') }}

SELECT
    md5(month_year)                                                  AS monthly_summary_id,
    month_year,
    COUNT(*)                                                         AS transaction_count,
    SUM(valor_transacao)                                             AS total_value_brl,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY valor_transacao)     AS kpi_median_price,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_per_m2)
        FILTER (WHERE price_per_m2 IS NOT NULL)                      AS kpi_median_price_per_m2,
    AVG(price_per_m2) FILTER (WHERE price_per_m2 IS NOT NULL)        AS avg_price_per_m2,
    CURRENT_TIMESTAMP                                                AS created_at

FROM {{ ref('silver_itbi_transactions') }}
GROUP BY month_year
ORDER BY month_year
```

**`itbi_sp/models/gold/gold_itbi_neighborhood_ranking.sql`:**
```sql
-- gold_itbi_neighborhood_ranking.sql
-- Contract version: v1.0 (2026-05-01)
-- Grain: one row per (bairro_normalized, month_year)
-- Feeds: Chart 2 — Neighborhood ranking + MoM appreciation
-- Note: rows with transaction_count < 3 are included but flagged for dashboard filtering

{{ config(materialized='table') }}

WITH base AS (
    SELECT
        bairro_normalized,
        month_year,
        COUNT(*)                                                              AS transaction_count,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY valor_transacao)         AS kpi_median_price,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_per_m2)
            FILTER (WHERE price_per_m2 IS NOT NULL)                          AS kpi_median_price_per_m2
    FROM {{ ref('silver_itbi_transactions') }}
    GROUP BY bairro_normalized, month_year
),

with_mom AS (
    SELECT
        *,
        LAG(kpi_median_price)
            OVER (PARTITION BY bairro_normalized ORDER BY month_year)        AS prev_median_price,
        LAG(kpi_median_price_per_m2)
            OVER (PARTITION BY bairro_normalized ORDER BY month_year)        AS prev_median_price_per_m2
    FROM base
)

SELECT
    md5(bairro_normalized || '|' || month_year)                       AS neighborhood_month_id,
    bairro_normalized,
    month_year,
    transaction_count,
    kpi_median_price,
    kpi_median_price_per_m2,
    CASE
        WHEN prev_median_price IS NULL OR prev_median_price = 0 THEN NULL
        ELSE ROUND(((kpi_median_price - prev_median_price) / prev_median_price) * 100, 4)
    END                                                               AS kpi_mom_price_change_pct,
    CASE
        WHEN prev_median_price_per_m2 IS NULL OR prev_median_price_per_m2 = 0 THEN NULL
        ELSE ROUND(((kpi_median_price_per_m2 - prev_median_price_per_m2) / prev_median_price_per_m2) * 100, 4)
    END                                                               AS kpi_mom_price_per_m2_change_pct,
    CURRENT_TIMESTAMP                                                 AS created_at

FROM with_mom
```

**`itbi_sp/models/gold/gold_itbi_price_per_m2.sql`:**
```sql
-- gold_itbi_price_per_m2.sql
-- Contract version: v1.0 (2026-05-01)
-- Grain: one row per (bairro_normalized, uso_desc, month_year)
-- Only rows where price_per_m2 IS NOT NULL (area_construida_m2 > 0)
-- Feeds: Chart 3 — Price per m² trend by neighborhood and use type

{{ config(materialized='table') }}

SELECT
    md5(
        bairro_normalized || '|' ||
        COALESCE(uso_desc, 'UNKNOWN') || '|' ||
        month_year
    )                                                                  AS price_m2_id,
    bairro_normalized,
    COALESCE(uso_desc, 'UNKNOWN')                                      AS uso_desc,
    month_year,
    COUNT(*)                                                           AS transaction_count,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_per_m2)         AS kpi_median_price_per_m2,
    AVG(price_per_m2)                                                  AS kpi_avg_price_per_m2,
    CURRENT_TIMESTAMP                                                  AS created_at

FROM {{ ref('silver_itbi_transactions') }}
WHERE price_per_m2 IS NOT NULL

GROUP BY bairro_normalized, COALESCE(uso_desc, 'UNKNOWN'), month_year
```

---

### Step 5 — dbt Tests (`make dbt-test`)

Runs all tests defined in Silver and Gold `.yml` schema files. CRITICAL tests block release. See Section 2 of `test_plan.md` for full test table.

---

## 6. Failure Handling

### Retry Policy

| Stage | Behavior on failure |
|---|---|
| Ingestion (Bronze) | Non-retryable within same run. Fix source file and re-run `make ingest`. Delete-first idempotency means re-run is safe. |
| Soda Bronze checks | CRITICAL failures halt the pipeline (exit code != 0). HIGH failures warn but do not halt. Re-run after fixing source data or investigating anomaly. |
| dbt seed | Non-retryable. If seed CSV is malformed, fix and re-run `make dbt-seed`. |
| dbt run | Non-retryable within run. Fix model SQL or source data and re-run `make dbt-run`. Silver full refresh is idempotent. |
| dbt test | CRITICAL test failures require investigation before pipeline is considered complete. HIGH failures require Coordinator exception to proceed. |
| Streamlit serve | Can be restarted independently via `make serve` without re-running upstream steps. |

### Idempotency Design

- **Bronze:** Delete-before-insert per `source_sheet`. Re-running `make ingest` for the same file is always safe. Row counts remain consistent.
- **Silver:** `materialized: table` — full table is dropped and recreated on every `dbt run`. No incremental state to corrupt.
- **Gold:** Same as Silver — full refresh, idempotent.
- **Seeds:** dbt truncates and reloads seeds on every `dbt seed`. Idempotent.

### Alerting

- Ingestion logs written to `logs/ingestion_<timestamp>.log` — check for WARNING/ERROR entries after each run.
- Soda Core check failures printed to stdout with FAIL/WARN status and metric values.
- dbt test failures displayed in stdout with failing row counts and SQL.
- No external alerting configured in v1. Tier 2 SLA — manual monitoring expected.

---

## 7. Virtual Environment Setup (MANDATORY)

All Python dependencies are installed inside `.venv` — no global installs permitted. There is no `sudo pip install`, `pip install --user`, or bare `pip install` used anywhere in this pipeline.

### 7.1 Create Virtual Environment

```bash
# Using standard Python venv (recommended)
python -m venv .venv

# OR using uv (faster alternative)
uv venv .venv
```

### 7.2 Activate Virtual Environment

**Linux / macOS:**
```bash
source .venv/bin/activate
```

**Windows:**
```cmd
.venv\Scripts\activate
```

### 7.3 Install Dependencies

```bash
# After activating .venv:
pip install -r requirements.txt
```

### 7.4 Complete `requirements.txt` (exact, with version pins)

```
# ITBI SP Dashboard Pipeline
# Python 3.11.x required
# All packages install inside .venv — no global installs

# dbt core + DuckDB adapter
dbt-core>=1.7.0,<2.0.0
dbt-duckdb>=1.7.0,<2.0.0

# Streamlit dashboard
streamlit>=1.32.0,<2.0.0

# Data quality
soda-core>=3.0.0,<4.0.0
soda-core-duckdb>=3.0.0,<4.0.0

# Ingestion
openpyxl>=3.1.0,<4.0.0

# DuckDB Python driver (ensure version alignment with dbt-duckdb)
duckdb>=0.10.0,<2.0.0

# Environment management
python-dotenv>=1.0.0,<2.0.0

# Utilities (transitive, pinned for reproducibility)
pandas>=2.0.0,<3.0.0
pyarrow>=14.0.0,<18.0.0
```

### 7.5 Dependency Confirmation

**All dependencies installed inside `.venv` — no global installs.**

Verify with:
```bash
which python   # should show .venv/bin/python
which dbt      # should show .venv/bin/dbt
which soda     # should show .venv/bin/soda
which streamlit # should show .venv/bin/streamlit
```

---

## 8. Complete Makefile

```makefile
# ITBI SP Dashboard Pipeline — Makefile
# Orchestration: GNU Make (no daemon, no cron)
# All Python tools run inside .venv/ — no global installs

.PHONY: venv install ingest soda-bronze dbt-seed dbt-run dbt-test serve pipeline clean help

PYTHON   = .venv/bin/python
DBT      = .venv/bin/dbt
SODA     = .venv/bin/soda
STREAMLIT = .venv/bin/streamlit

DBT_PROJECT_DIR = itbi_sp
DBT_PROFILES_DIR = itbi_sp
SODA_CONFIG     = itbi_sp/soda/configuration.yml
XLSX_FILE       = data/raw/itbi_sp_2026.xlsx

## ──────────────────────────────────────────────────────────────────────────
## Setup
## ──────────────────────────────────────────────────────────────────────────

venv: ## Create virtual environment (.venv)
	python -m venv .venv
	@echo "Run: source .venv/bin/activate"

install: ## Install all Python dependencies inside .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

## ──────────────────────────────────────────────────────────────────────────
## Pipeline steps
## ──────────────────────────────────────────────────────────────────────────

ingest: ## Ingest XLSX into DuckDB Bronze layer
	$(PYTHON) scripts/ingest.py --file $(XLSX_FILE)

soda-bronze: ## Run Soda Core DQ checks on Bronze layer
	$(SODA) scan \
	  -d itbi_duckdb \
	  -c $(SODA_CONFIG) \
	  itbi_sp/soda/checks/bronze_privacy_guard.yml
	$(SODA) scan \
	  -d itbi_duckdb \
	  -c $(SODA_CONFIG) \
	  itbi_sp/soda/checks/bronze_itbi_transactions.yml

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

pipeline: ingest soda-bronze dbt-seed dbt-run dbt-test ## Run full pipeline (ingest → DQ → seeds → transform → test)
	@echo "Pipeline complete. Run 'make serve' to start the dashboard."

## ──────────────────────────────────────────────────────────────────────────
## Maintenance
## ──────────────────────────────────────────────────────────────────────────

clean: ## Remove dbt target artifacts and logs older than 7 days
	rm -rf itbi_sp/target itbi_sp/logs
	find logs/ -name "*.log" -mtime +7 -delete

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
```

---

## 9. dbt Project Structure

```
itbi_sp/                                  # dbt project root
  dbt_project.yml                         # Project name, paths, materialization defaults
  profiles.yml                            # DuckDB connection; DB_PATH from .env; NOT committed
  models/
    bronze/
      bronze_itbi_transactions.sql        # Source reference view (Bronze is loaded by Python ingest)
      bronze_itbi_transactions.yml        # Source definition for dbt lineage
    silver/
      silver_itbi_transactions.sql        # Sub-step 1 (typing) + Sub-step 2 (standardization) as CTEs
      silver_itbi_transactions.yml        # not_null, unique, expression_is_true, RI tests
    gold/
      gold_itbi_monthly_summary.sql
      gold_itbi_neighborhood_ranking.sql
      gold_itbi_price_per_m2.sql
      gold_itbi_monthly_summary.yml
      gold_itbi_neighborhood_ranking.yml
      gold_itbi_price_per_m2.yml
  macros/
    normalize_bairro.sql                  # Accent strip + abbreviation expansion macro
  seeds/
    seed_uso_lookup.csv                   # IPTU use code lookup (from "Tabela de USOS" sheet)
    seed_padrao_lookup.csv                # IPTU standard lookup (from "Tabela de PADRÕES" sheet)
  soda/
    configuration.yml                     # Soda Core data source config (DuckDB)
    checks/
      bronze_itbi_transactions.yml        # Freshness, null, row count, composite key checks
      bronze_privacy_guard.yml            # Schema check: privacy columns must be absent

scripts/
  ingest.py                               # Python Bronze ingestion script (openpyxl → DuckDB)

app/
  streamlit_app.py                        # Streamlit dashboard (read-only DuckDB on Gold tables)

data/
  raw/
    itbi_sp_2026.xlsx                     # XLSX source file (NOT committed to git)

logs/
  ingestion_<timestamp>.log              # Per-run ingestion logs

.env                                      # DB_PATH=./... — NOT committed to git
.env.example                              # DB_PATH=./workspace/2026-05-01-itbi-sp-dashboard/build/itbi_sp.duckdb
.gitignore                                # Excludes: data/raw/*.xlsx, *.duckdb, .env, .venv/
Makefile
requirements.txt
```

**`dbt_project.yml` (key settings):**
```yaml
name: 'itbi_sp'
version: '1.0.0'
config-version: 2

profile: 'itbi_sp'

model-paths: ["models"]
seed-paths: ["seeds"]
macro-paths: ["macros"]
target-path: "target"
clean-targets: ["target", "dbt_packages"]

models:
  itbi_sp:
    bronze:
      +materialized: view        # Bronze is a passthrough source view
    silver:
      +materialized: table       # Full refresh
    gold:
      +materialized: table       # Full refresh
```

**`profiles.yml` (NOT committed — use `.env` for DB_PATH):**
```yaml
itbi_sp:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "{{ env_var('DB_PATH') }}"
      threads: 4
```

---

## 10. Operational Runbook

### Normal Monthly Run (new XLSX tab added)

```bash
# 1. Drop new XLSX file into data/raw/
# 2. Activate virtual environment
source .venv/bin/activate

# 3. Run full pipeline
make pipeline

# 4. If pipeline passes all tests, start dashboard
make serve
```

### Re-ingesting a Corrected Sheet

If a monthly sheet had errors and a corrected XLSX is provided:

```bash
# Re-run ingest only — delete-before-insert ensures no duplicates
make ingest

# Re-run full downstream transform + test
make soda-bronze && make dbt-run && make dbt-test
```

### Backfilling Historical Sheets

If a new XLSX contains multiple months not yet in DuckDB:

```bash
# No pipeline code changes needed — sheet detection is automatic.
# All matching sheets not yet in Bronze will be ingested.
# If sheets already exist in Bronze, they will be deleted and re-inserted (idempotent).
make ingest
make soda-bronze
make dbt-seed
make dbt-run
make dbt-test
```

### Common Failure Modes

| Symptom | Likely cause | Resolution |
|---|---|---|
| `DB_PATH not set` | `.env` file missing | Copy `.env.example` to `.env`; set `DB_PATH` |
| `XLSX file not found` | Wrong path or file not dropped | Verify file at `data/raw/itbi_sp_2026.xlsx` |
| `No sheets matching pattern` | Sheet names don't match `^[A-Z]{3}-\d{4}$` | Inspect workbook tab names; update regex if PMSP changed naming |
| Soda `privacy_columns_absent` FAIL | Privacy column appeared in schema | Investigate ingestion script; column should never be written |
| Soda `monthly_load_freshness` FAIL | File not dropped for 35+ days | Coordinate with data owner for missing months |
| dbt `unique.transaction_id` FAIL | Duplicate transactions in source | Investigate Bronze duplicates; source may have re-issued rows |
| dbt `expression_is_true.valor_transacao > 0` FAIL | Silver filter logic broken | Inspect Silver CTE `typed` — verify `WHERE` clause |
| `PERCENTILE_CONT` error in Gold | DuckDB version mismatch | Upgrade DuckDB to >= 0.10.x |
| Streamlit blank charts | Gold tables empty | Run `make pipeline` before `make serve` |
| MoM KPIs all NULL in neighborhood ranking | Only one month of data loaded | Expected behavior — LAG returns NULL for first observed month per bairro |

### Adding a New Year's Workbook

When PMSP publishes `itbi_sp_2027.xlsx`:

```bash
# Update XLSX_FILE in Makefile to point to new file, OR
# Pass file path explicitly:
python scripts/ingest.py --file data/raw/itbi_sp_2027.xlsx
# Remainder of pipeline unchanged
```
