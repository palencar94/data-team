# ITBI SP — Dashboard Reference

**App file:** `app/streamlit_app.py`
**URL:** `http://localhost:8501`
**Launch:** `make serve`
**Stack:** Streamlit + DuckDB (read-only connection) + Plotly + Pandas

---

## Dashboard Structure

### Sidebar
- Period selector (month_year range filter applied to all sections)
- Minimum transaction count toggle (filters low-volume neighborhoods in ranking)
- Data freshness notice (max `ingested_at` from Silver)

---

### Section A — City-Wide Trends
**Source:** `gold_itbi_monthly_summary`

| Chart | Type | X | Y | Description |
|-------|------|---|---|-------------|
| A1 | Line + Bar (dual-axis) | month_year | kpi_median_price (line), transaction_count (bar) | Month-over-month median price evolution |
| A2 | Area fill | month_year | kpi_median_price_per_m2 | Median price per m² trend |
| Metric cards | KPI tiles | — | Latest month: median price, median price/m², transaction count | Top-of-page summary |

---

### Section B — Neighborhood Ranking
**Source:** `gold_itbi_neighborhood_ranking`

| Chart | Type | Description |
|-------|------|-------------|
| B1 | Horizontal bar | Top N neighborhoods by median price for selected period |
| B2 | Styled DataFrame | Sortable table: bairro, transaction_count, kpi_median_price, kpi_median_price_per_m2, kpi_mom_price_change_pct |

---

### Section C — Price per m² Drill-down
**Source:** `gold_itbi_price_per_m2`

| Chart | Type | Description |
|-------|------|-------------|
| C1 | Multi-series line | Price/m² over time for selected neighborhoods, broken by uso_desc |
| C2 | Grouped bar | Price/m² comparison across neighborhoods for selected use type and month |

---

## KPIs Implemented

All KPIs are computed in Gold layer. The dashboard reads Gold tables read-only — no calculations in the Streamlit app.

| KPI | Formula | Source Table | Notes |
|-----|---------|-------------|-------|
| Median transaction price | PERCENTILE_CONT(0.5) of valor_transacao | gold_itbi_monthly_summary, gold_itbi_neighborhood_ranking | |
| Median price per m² | PERCENTILE_CONT(0.5) of price_per_m2 | All Gold tables | Only rows with area_construida_m2 > 0 |
| Transaction count | COUNT(*) | All Gold tables | |
| MoM price change % | (current - prev) / prev * 100 | gold_itbi_neighborhood_ranking | NULL for first month of each neighborhood |
| Total value BRL | SUM(valor_transacao) | gold_itbi_monthly_summary | |

---

## DuckDB Connection Pattern

```python
@st.cache_resource
def get_connection():
    return duckdb.connect(os.environ["DB_PATH"], read_only=True)
```

**Read-only mode** is required to allow concurrent read access while keeping writes locked to the pipeline. This means the dashboard cannot start a dbt run or ingest.

---

## Adding a New Chart

1. Confirm the required data is in a Gold table (do not query Silver or Bronze in the dashboard)
2. Add any new aggregations to the relevant Gold model SQL
3. Run `make dbt-run` to refresh
4. Add the chart to `app/streamlit_app.py`

---

## Known Dashboard Caveats

- **Pre-2026 outlier months:** `gold_itbi_monthly_summary` contains months back to 1995 from a few historical transactions embedded in the source file. The period selector in the sidebar defaults to 2026 to filter these out.
- **Low-volume neighborhoods:** Neighborhoods with 1-2 transactions show extreme MoM swings. Enable the minimum transaction count filter (≥5 recommended) in the sidebar when interpreting trends.
- **price_per_m2 = 0 rows:** 22 rows in `gold_itbi_price_per_m2` have `kpi_median_price_per_m2 = 0` due to token-value transactions. These are visible in Section C but have negligible impact on trends.
