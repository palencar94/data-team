# BI Handoff Note
## Request ID: 2026-05-01-itbi-sp-dashboard
## Version: v1.0 — 2026-05-01
## From: Data Engineer
## To: BI Specialist (Streamlit dashboard implementation)

---

## 1. Gold Tables Available

All three Gold tables are materialized as DuckDB tables (full refresh). They are the **only** layer the Streamlit dashboard may query — Bronze and Silver are internal pipeline layers and must not be exposed in the app.

The Streamlit app must open DuckDB in **read-only mode**:
```python
import duckdb, os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.environ["DB_PATH"]

@st.cache_resource
def get_connection():
    return duckdb.connect(DB_PATH, read_only=True)
```

All queries must use `@st.cache_data` with an appropriate TTL (e.g. `ttl=3600`) to avoid re-querying the file on every interaction.

---

### 1.1 `gold_itbi_monthly_summary`

**Grain:** One row per calendar month across all São Paulo.
**Primary key:** `monthly_summary_id` (VARCHAR — md5 of month_year)
**Time dimension:** `month_year` (VARCHAR, format `YYYY-MM`, e.g. `2026-01`)

| Column | Type | Nullable | Description |
|---|---|---|---|
| `monthly_summary_id` | VARCHAR | NOT NULL | Surrogate PK |
| `month_year` | VARCHAR | NOT NULL | Calendar month YYYY-MM |
| `transaction_count` | INTEGER | NOT NULL | Total qualifying transactions |
| `total_value_brl` | DECIMAL(20,2) | NOT NULL | Sum of all declared values (BRL) |
| `kpi_median_price` | DECIMAL(18,2) | YES | Median transaction price (BRL) — use for MoM trend chart |
| `kpi_median_price_per_m2` | DECIMAL(18,2) | YES | Median price per m² across all built-area transactions |
| `avg_price_per_m2` | DECIMAL(18,2) | YES | Mean price per m² (supplementary — prefer median for display) |
| `created_at` | TIMESTAMP | NOT NULL | Row write timestamp |

**Dashboard use:** Chart 1 — Month-over-month price evolution.

---

### 1.2 `gold_itbi_neighborhood_ranking`

**Grain:** One row per (bairro_normalized, month_year) combination.
**Primary key:** `neighborhood_month_id` (VARCHAR — md5 of bairro_normalized + month_year)
**Dimensions:** `bairro_normalized` (VARCHAR), `month_year` (VARCHAR)

| Column | Type | Nullable | Description |
|---|---|---|---|
| `neighborhood_month_id` | VARCHAR | NOT NULL | Surrogate PK |
| `bairro_normalized` | VARCHAR | NOT NULL | Normalized neighborhood name (uppercase, no accents, abbreviations expanded) |
| `month_year` | VARCHAR | NOT NULL | Calendar month YYYY-MM |
| `transaction_count` | INTEGER | NOT NULL | Transactions in this bairro + month |
| `kpi_median_price` | DECIMAL(18,2) | YES | Median transaction value (BRL) |
| `kpi_median_price_per_m2` | DECIMAL(18,2) | YES | Median price per m² |
| `kpi_mom_price_change_pct` | DECIMAL(10,4) | YES | MoM change in median price (%) — NULL for first observed month per bairro |
| `kpi_mom_price_per_m2_change_pct` | DECIMAL(10,4) | YES | MoM change in median price/m² (%) — NULL for first month |
| `created_at` | TIMESTAMP | NOT NULL | Row write timestamp |

**Dashboard use:** Chart 2 — Neighborhood ranking + appreciation table.

**Low-volume flag:** Rows where `transaction_count < 3` are statistically unstable and **must be filtered out by default** in the ranking display (a UI toggle can optionally re-include them). Do not rank single-transaction bairros alongside those with dozens of transactions in a given month.

---

### 1.3 `gold_itbi_price_per_m2`

**Grain:** One row per (bairro_normalized, uso_desc, month_year) where at least one transaction has a valid built area (price_per_m2 IS NOT NULL).
**Primary key:** `price_m2_id` (VARCHAR — md5 of bairro_normalized + uso_desc + month_year)
**Dimensions:** `bairro_normalized`, `uso_desc`, `month_year`

| Column | Type | Nullable | Description |
|---|---|---|---|
| `price_m2_id` | VARCHAR | NOT NULL | Surrogate PK |
| `bairro_normalized` | VARCHAR | NOT NULL | Normalized neighborhood name |
| `uso_desc` | VARCHAR | NOT NULL | Canonical use type description (e.g. RESIDENCIAL UNIFAMILIAR, COMERCIAL); value `'UNKNOWN'` when source code had no lookup match |
| `month_year` | VARCHAR | NOT NULL | Calendar month YYYY-MM |
| `transaction_count` | INTEGER | NOT NULL | Transactions with valid built area in this segment |
| `kpi_median_price_per_m2` | DECIMAL(18,2) | YES | Median price/m² for this segment |
| `kpi_avg_price_per_m2` | DECIMAL(18,2) | YES | Mean price/m² (supplementary) |
| `created_at` | TIMESTAMP | NOT NULL | Row write timestamp |

**Dashboard use:** Chart 3 — Price per m² trend by neighborhood and use type.

**Note:** This table only includes transactions where `area_construida_m2 > 0`. Pure land transactions (area = 0) are excluded by design. This is expected behavior — not a data issue.

---

## 2. Exact DuckDB Queries for Dashboard Charts

### Chart 1 — Month-over-Month Price Evolution (city-wide)

**Purpose:** Line chart showing median transaction price and median price/m² per month.

```python
@st.cache_data(ttl=3600)
def query_monthly_trend(_con) -> "pd.DataFrame":
    return _con.execute("""
        SELECT
            month_year,
            transaction_count,
            total_value_brl,
            kpi_median_price,
            kpi_median_price_per_m2,
            avg_price_per_m2
        FROM gold_itbi_monthly_summary
        ORDER BY month_year ASC
    """).df()
```

**Plotly usage guidance:**
- X-axis: `month_year` (string, sorted ascending)
- Primary Y-axis: `kpi_median_price` (BRL) — format as `R$ {:,.0f}`
- Secondary Y-axis: `kpi_median_price_per_m2` (BRL/m²)
- Tooltip: include `transaction_count` and `total_value_brl`
- If `kpi_median_price` IS NULL for a month, that month has no price/m² data (all transactions were land-only) — display a gap in the line, not zero.

---

### Chart 2 — Neighborhood Ranking Table

**Purpose:** Ranked table of neighborhoods by median price or MoM appreciation for a selected month.

```python
@st.cache_data(ttl=3600)
def query_neighborhood_ranking(_con, selected_month: str, min_transactions: int = 3) -> "pd.DataFrame":
    return _con.execute("""
        SELECT
            bairro_normalized                      AS bairro,
            transaction_count,
            kpi_median_price,
            kpi_median_price_per_m2,
            kpi_mom_price_change_pct,
            kpi_mom_price_per_m2_change_pct
        FROM gold_itbi_neighborhood_ranking
        WHERE month_year = ?
          AND transaction_count >= ?
        ORDER BY kpi_median_price_per_m2 DESC NULLS LAST
    """, [selected_month, min_transactions]).df()
```

**Filter UI:**
- `selected_month`: dropdown populated from `SELECT DISTINCT month_year FROM gold_itbi_monthly_summary ORDER BY 1 DESC` (default: most recent month)
- `min_transactions`: slider defaulting to 3 (minimum transaction threshold for statistical stability)
- Optional: secondary sort button by `kpi_mom_price_change_pct` (top appreciating bairros)

**MoM display:**
- Format `kpi_mom_price_change_pct` as `+X.XX%` / `-X.XX%` with color coding (green = appreciation, red = depreciation)
- NULL MoM means first observed month for that bairro — display as `—` (em dash), not 0%

---

### Chart 3 — Price per m² Trend by Neighborhood and Use Type

**Purpose:** Line chart of median price/m² over time for a selected bairro, broken out by use type.

```python
@st.cache_data(ttl=3600)
def query_price_per_m2_trend(
    _con,
    selected_bairro: str,
    selected_uso: list[str] | None = None,
) -> "pd.DataFrame":
    if selected_uso:
        placeholders = ", ".join(["?" for _ in selected_uso])
        params = [selected_bairro] + selected_uso
        filter_clause = f"AND uso_desc IN ({placeholders})"
    else:
        params = [selected_bairro]
        filter_clause = ""

    return _con.execute(f"""
        SELECT
            month_year,
            uso_desc,
            transaction_count,
            kpi_median_price_per_m2,
            kpi_avg_price_per_m2
        FROM gold_itbi_price_per_m2
        WHERE bairro_normalized = ?
          {filter_clause}
        ORDER BY month_year ASC, uso_desc ASC
    """, params).df()


@st.cache_data(ttl=3600)
def get_available_bairros(_con) -> list[str]:
    """Populate bairro selector — only bairros with price/m2 data."""
    return [
        row[0]
        for row in _con.execute("""
            SELECT DISTINCT bairro_normalized
            FROM gold_itbi_price_per_m2
            ORDER BY bairro_normalized ASC
        """).fetchall()
    ]


@st.cache_data(ttl=3600)
def get_available_uso_types(_con, bairro: str) -> list[str]:
    """Populate use type multiselect for a given bairro."""
    return [
        row[0]
        for row in _con.execute("""
            SELECT DISTINCT uso_desc
            FROM gold_itbi_price_per_m2
            WHERE bairro_normalized = ?
            ORDER BY uso_desc ASC
        """, [bairro]).fetchall()
    ]
```

**Plotly usage guidance:**
- X-axis: `month_year` (sorted ascending)
- Y-axis: `kpi_median_price_per_m2` (BRL/m²)
- One line per `uso_desc` (color-coded)
- Tooltip: include `transaction_count` for the segment — helps user assess reliability
- Suppress lines for segments where `transaction_count < 3` or display with a dashed/low-opacity style to indicate low confidence

---

### Supporting Query: Month Selector Initialization

```python
@st.cache_data(ttl=3600)
def get_available_months(_con) -> list[str]:
    return [
        row[0]
        for row in _con.execute("""
            SELECT DISTINCT month_year
            FROM gold_itbi_monthly_summary
            ORDER BY month_year DESC
        """).fetchall()
    ]
```

---

## 3. Expected Joins and Filters

### 3.1 No Joins Required Across Gold Tables

All three Gold tables are fully self-contained — no cross-table JOINs are needed for the dashboard charts. Each table has all the dimensions and KPIs required for its corresponding chart.

### 3.2 Consistent Filter Dimension: `month_year`

`month_year` is the shared time key across all three tables (VARCHAR, format `YYYY-MM`). If a global month selector is used in the dashboard sidebar, it can filter across all three charts consistently:

```python
# Safe equality filter (DuckDB parametric)
WHERE month_year = ?
```

### 3.3 Consistent Filter Dimension: `bairro_normalized`

`bairro_normalized` is the shared neighborhood key in `gold_itbi_neighborhood_ranking` and `gold_itbi_price_per_m2`. When a user selects a bairro in Chart 2, Chart 3 should auto-filter to the same bairro.

```python
# Example: bairro drilldown from Chart 2 to Chart 3
WHERE bairro_normalized = ?
```

**Important:** `bairro_normalized` values in the Gold tables have been normalized (uppercase, no accents, abbreviations expanded). The UI selector must be populated from the actual Gold table values — do not use raw source bairro strings as filter inputs.

### 3.4 Use Type Filter for Chart 3

The `uso_desc` column in `gold_itbi_price_per_m2` is the canonical use type description. Recommended filter: multi-select checkbox allowing the user to isolate RESIDENCIAL vs. COMERCIAL segments. Use `get_available_uso_types()` query above to dynamically populate the options for the selected bairro.

---

## 4. Data Caveats the BI Layer Must Surface

The following caveats must be visible in the dashboard — either as persistent info boxes, tooltips on chart elements, or a dedicated "About the Data" section. Do not silently suppress these behaviors.

### 4.1 Delayed ITBI Registration

ITBI declarations can be registered weeks or months after the physical property transfer. The `data_transacao` field reflects the ITBI declaration date, not necessarily the real estate transaction date. A row appearing in sheet `MAR-2026` may have `data_transacao` of December 2025.

**Dashboard note to expose:** "Transaction dates reflect ITBI declaration dates, which may lag property transfer dates by several months. Month-over-month trends are based on declaration date, not transfer date."

### 4.2 Land-Only Transactions Excluded from price/m²

Properties with `area_construida_m2 = 0` (pure land transactions) have no `price_per_m2` value and are excluded from `gold_itbi_price_per_m2`. They are still counted in `gold_itbi_monthly_summary` and `gold_itbi_neighborhood_ranking`.

**Dashboard note to expose:** "Price per m² statistics exclude land-only transactions (built area = 0). Charts involving price/m² represent only transactions with registered built area."

### 4.3 Low-Volume Bairros (transaction_count < 3)

Neighborhoods with fewer than 3 transactions in a given month produce statistically unreliable median and MoM KPIs. These rows exist in `gold_itbi_neighborhood_ranking` and `gold_itbi_price_per_m2` but should be filtered from the default ranking view.

**Dashboard behavior:**
- Default: hide bairros with `transaction_count < 3` in Chart 2 ranking and Chart 3 trend lines
- Optional UI toggle: "Show all neighborhoods (including low-volume)" to re-include them with a visual warning indicator

**Dashboard note to expose:** "Neighborhoods with fewer than 3 transactions in a month are hidden by default. Their KPIs may not be statistically representative."

### 4.4 First-Month MoM is Always NULL

For the first month a neighborhood appears in the dataset (or after a gap in data), `kpi_mom_price_change_pct` and `kpi_mom_price_per_m2_change_pct` will be NULL (no prior month to compare against).

**Dashboard behavior:** Display NULL MoM as `—` (em dash), not `0%`. Do not sort NULLs to the top of the appreciation ranking.

### 4.5 Valor Venal de Referência = 0 Means No IPTU Reference

`valor_venal_referencia = 0` in the source means the property is absent from the PMSP IPTU reference database — it does not mean the property is worthless. This value is set to NULL in Silver and Gold. The dashboard should not display or compare this field as if 0 were a valid monetary value.

### 4.6 use_desc = 'UNKNOWN' Rows

If a transaction's `uso_iptu_codigo` did not match any entry in `seed_uso_lookup`, it is represented as `uso_desc = 'UNKNOWN'` in `gold_itbi_price_per_m2`. This indicates that the seed tables may need updating with new PMSP use codes.

**Dashboard behavior:** Include `UNKNOWN` in the use type selector but label it clearly as "Use type not resolved" rather than displaying the raw `UNKNOWN` string.

### 4.7 Declared Value vs. Market Value

`valor_transacao` is the **declared value** by the taxpayer, not an appraised or market value. Parties may have incentive to under- or over-declare. The median (not mean) is used as the KPI to reduce sensitivity to outlier declarations, but the underlying data quality limitation applies.

**Dashboard note to expose:** "Transaction values are self-declared by taxpayers (ITBI declaration). They may not reflect full market prices. Median values are used to reduce outlier sensitivity."

### 4.8 Surrogate Key Collision Notice

`transaction_id` is an MD5 hash. MD5 collision probability at typical ITBI dataset sizes (tens of thousands of rows per month) is negligible but nonzero. If the `unique.transaction_id` dbt test fails, investigate whether it is a genuine duplicate transaction (source re-issuance) or an MD5 collision before taking pipeline action.

---

## 5. Technical Integration Notes

### 5.1 DuckDB Connection in Streamlit

```python
# app/streamlit_app.py — recommended connection pattern
import duckdb
import streamlit as st
from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = os.environ["DB_PATH"]

@st.cache_resource
def get_con():
    # Read-only connection — Gold tables only
    return duckdb.connect(DB_PATH, read_only=True)

con = get_con()
```

Use `@st.cache_resource` for the connection object (persists across re-renders) and `@st.cache_data(ttl=3600)` on each query function (cached for 1 hour, refreshed after pipeline re-run).

### 5.2 Numeric Formatting

| Metric | Recommended format |
|---|---|
| Median price (BRL) | `R$ {:,.0f}` (e.g. R$ 650,000) |
| Median price/m² (BRL/m²) | `R$ {:,.0f}/m²` |
| MoM change (%) | `+X.XX%` / `-X.XX%` with sign |
| Transaction count | `{:,}` (e.g. 1,234) |
| Total value BRL | `R$ {:,.0f}` or abbreviated `R$ X.X M` |

### 5.3 Month Display Format

`month_year` is stored as `YYYY-MM` (e.g. `2026-01`). For display, convert to Portuguese month names:

```python
MONTH_PT = {
    "01": "Janeiro", "02": "Fevereiro", "03": "Março",
    "04": "Abril",   "05": "Maio",      "06": "Junho",
    "07": "Julho",   "08": "Agosto",    "09": "Setembro",
    "10": "Outubro", "11": "Novembro",  "12": "Dezembro",
}

def fmt_month(month_year: str) -> str:
    year, month = month_year.split("-")
    return f"{MONTH_PT[month]}/{year}"  # e.g. "Janeiro/2026"
```

### 5.4 Color Coding for MoM

```python
def color_mom(val):
    """Streamlit dataframe style: green for positive, red for negative MoM."""
    if val is None or str(val) == "nan":
        return "color: gray"
    return "color: green" if val > 0 else "color: red"
```

---

## 6. Dashboard Architecture Reference

```
app/streamlit_app.py
  ├── Sidebar: global filters (month selector, bairro selector, min_transactions threshold)
  ├── Section 1 — City-wide Trends
  │     └── Chart 1: Plotly line chart — monthly median price + price/m² trend
  │           Query: gold_itbi_monthly_summary
  ├── Section 2 — Neighborhood Ranking
  │     └── Chart 2: Streamlit dataframe (styled) — bairros ranked by kpi_median_price_per_m2
  │           Query: gold_itbi_neighborhood_ranking (filtered by month + min_transactions)
  │           Includes MoM change column with color coding
  └── Section 3 — Price per m² Drill-down
        └── Chart 3: Plotly line chart — price/m² over time for selected bairro, by uso_desc
              Query: gold_itbi_price_per_m2 (filtered by bairro + uso type multiselect)
```

---

## 7. Handoff Checklist

Before beginning dashboard implementation, verify:

- [ ] `make pipeline` has been run successfully to completion
- [ ] `make dbt-test` passed with 0 CRITICAL failures
- [ ] DuckDB file exists at `DB_PATH` (check `.env`)
- [ ] `gold_itbi_monthly_summary` is non-empty: `SELECT COUNT(*) FROM gold_itbi_monthly_summary`
- [ ] `gold_itbi_neighborhood_ranking` is non-empty
- [ ] `gold_itbi_price_per_m2` is non-empty
- [ ] `seed_uso_lookup` and `seed_padrao_lookup` are loaded and populated
- [ ] `.venv` is activated and `streamlit` is available: `which streamlit`
- [ ] `test_plan.md` sign-off section is completed and approved

**BI Specialist is cleared to begin dashboard implementation once all items above are confirmed.**
