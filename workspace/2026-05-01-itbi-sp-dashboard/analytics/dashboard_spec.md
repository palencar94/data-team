# Dashboard Specification
## Request ID: 2026-05-01-itbi-sp-dashboard
## Produced by: BI Specialist
## Date: 2026-05-01

---

## Audience

Paulo Guilherme Alencar — real estate investor and end user. Single-user deployment on local machine. The stakeholder combines domain knowledge of São Paulo's real estate market with data literacy (Python, SQL, Streamlit). The dashboard must support self-service exploration without BI intermediaries.

---

## Decisions Supported

1. **Investment targeting:** Identify which neighborhoods show the strongest upward price trend in early 2026 to prioritize acquisition due diligence.
2. **Price benchmarking:** Determine whether a prospective transaction price per m² is above or below the neighborhood median for the current month.
3. **Market timing:** Assess whether the city-wide median transaction price is trending up, flat, or down month-over-month to inform deal timing.
4. **Property type allocation:** Compare price/m² appreciation across use types (RESIDENCIA, APARTAMENTO, COMERCIAL, etc.) to identify the segment with the highest momentum.
5. **Risk filtering:** Exclude low-volume neighborhoods (< 3 transactions/month) whose KPIs have high statistical uncertainty.

---

## Section 1 — KPI Set

### KPI 1: Median Transaction Price

| Field | Value |
|---|---|
| **Name** | `kpi_median_price` |
| **Business definition** | The median declared ITBI transaction value in BRL for all qualifying transactions within the scope grain. "Declared" means the value reported by the buyer on the ITBI form — it may not fully reflect market price. Median is used (not mean) to reduce sensitivity to outlier high-value transactions. |
| **Formula** | `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY valor_transacao)` over all transactions where `valor_transacao > 0` |
| **Grain** | Month (city-wide): one value per `month_year` in `gold_itbi_monthly_summary`. Neighborhood-month: one value per `(bairro_normalized, month_year)` in `gold_itbi_neighborhood_ranking`. |
| **Dimensions** | `month_year`, `bairro_normalized` (for neighborhood grain) |
| **Source gold model** | `gold_itbi_monthly_summary` (city-wide), `gold_itbi_neighborhood_ranking` (neighborhood) |
| **Owner** | Paulo Guilherme Alencar |
| **Caveats** | (1) Transaction dates are ITBI declaration dates, not property transfer dates — may lag actual market activity by weeks or months. (2) Values are self-declared by buyers; median reduces but does not eliminate outlier influence. (3) First month in the dataset has no prior-month baseline — MoM change is NULL. |

---

### KPI 2: Median Price per m²

| Field | Value |
|---|---|
| **Name** | `kpi_median_price_per_m2` |
| **Business definition** | The median declared transaction price divided by the built area (area_construida_m2) in BRL/m², for all qualifying transactions where built area is greater than zero. Land-only transactions (area_construida_m2 = 0 or NULL) are excluded — this KPI measures built real estate only. |
| **Formula** | `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_per_m2) FILTER (WHERE price_per_m2 IS NOT NULL)` where `price_per_m2 = ROUND(valor_transacao / area_construida_m2, 2)` computed at Silver layer |
| **Grain** | Month (city-wide): one value per `month_year` in `gold_itbi_monthly_summary`. Neighborhood-month: one value per `(bairro_normalized, month_year)` in `gold_itbi_neighborhood_ranking`. Segment: one value per `(bairro_normalized, uso_desc, month_year)` in `gold_itbi_price_per_m2`. |
| **Dimensions** | `month_year`, `bairro_normalized`, `uso_desc` |
| **Source gold model** | `gold_itbi_monthly_summary`, `gold_itbi_neighborhood_ranking`, `gold_itbi_price_per_m2` |
| **Owner** | Paulo Guilherme Alencar |
| **Caveats** | (1) Excludes land-only transactions (area_construida_m2 = 0 or NULL) — share of excluded transactions varies by neighborhood and may bias comparisons. (2) Valor Venal de Referência = 0 in source means no IPTU reference exists (stored as NULL in Silver/Gold) — does not affect this KPI's formula but may affect future ratio analyses. (3) For segments with very few transactions, median is statistically unreliable — hide bairros with transaction_count < 3 by default. |

---

### KPI 3: MoM Price Change

| Field | Value |
|---|---|
| **Name** | `kpi_mom_price_change_pct` |
| **Business definition** | Month-over-month percentage change in the median declared transaction price, computed per neighborhood. Positive values indicate appreciation; negative values indicate decline. NULL for the first observed month of a neighborhood (no prior baseline). |
| **Formula** | `ROUND(((kpi_median_price - LAG(kpi_median_price) OVER (PARTITION BY bairro_normalized ORDER BY month_year)) / LAG(kpi_median_price) OVER (PARTITION BY bairro_normalized ORDER BY month_year)) * 100, 4)` — NULL when LAG is NULL or zero |
| **Grain** | One value per `(bairro_normalized, month_year)` in `gold_itbi_neighborhood_ranking` |
| **Dimensions** | `bairro_normalized`, `month_year` |
| **Source gold model** | `gold_itbi_neighborhood_ranking` |
| **Owner** | Paulo Guilherme Alencar |
| **Caveats** | (1) First month per neighborhood always returns NULL — display as em dash (—), never as 0%. (2) A neighborhood with transaction_count < 3 in either the current or prior month produces an unreliable MoM figure — these are hidden by default behind the minimum-transaction toggle. (3) MoM compares consecutive months only; if a bairro has no transactions in a given month, the LAG will skip over that gap, producing a multi-month comparison mislabeled as one-month. This risk is negligible for the current 3-month window but must be documented. |

---

### KPI 4: MoM Price per m² Change

| Field | Value |
|---|---|
| **Name** | `kpi_mom_price_per_m2_change_pct` |
| **Business definition** | Month-over-month percentage change in the median price per built m², computed per neighborhood. Measures whether per-unit-area value is rising or falling independently of transaction size composition. NULL for the first observed month. |
| **Formula** | `ROUND(((kpi_median_price_per_m2 - LAG(kpi_median_price_per_m2) OVER (PARTITION BY bairro_normalized ORDER BY month_year)) / LAG(kpi_median_price_per_m2) OVER (PARTITION BY bairro_normalized ORDER BY month_year)) * 100, 4)` — NULL when LAG is NULL or zero |
| **Grain** | One value per `(bairro_normalized, month_year)` in `gold_itbi_neighborhood_ranking` |
| **Dimensions** | `bairro_normalized`, `month_year` |
| **Source gold model** | `gold_itbi_neighborhood_ranking` |
| **Owner** | Paulo Guilherme Alencar |
| **Caveats** | Same as KPI 3. Additionally: (1) This KPI only covers transactions with area_construida_m2 > 0; if a neighborhood's transaction mix shifts toward land-only deals in a given month, kpi_median_price_per_m2 may be NULL and MoM is therefore NULL even if kpi_median_price has data. (2) Interpret alongside transaction_count — a large MoM swing on < 10 transactions should be treated as directional signal only, not a confirmed trend. |

---

### KPI 5: Transaction Volume

| Field | Value |
|---|---|
| **Name** | `transaction_count` |
| **Business definition** | Count of qualifying ITBI transactions in the given scope (city-wide or neighborhood-month). A qualifying transaction has `valor_transacao > 0` after Silver-layer cleaning and deduplication by surrogate key. Transactions with invalid or zero declared value are excluded at the Silver layer and never reach Gold. |
| **Formula** | `COUNT(*)` after Silver filtering (`valor_transacao > 0`, deduplication by `transaction_id`) |
| **Grain** | Month (city-wide): one value per `month_year`. Neighborhood-month: one value per `(bairro_normalized, month_year)`. Segment: one value per `(bairro_normalized, uso_desc, month_year)`. |
| **Dimensions** | `month_year`, `bairro_normalized`, `uso_desc` |
| **Source gold model** | `gold_itbi_monthly_summary`, `gold_itbi_neighborhood_ranking`, `gold_itbi_price_per_m2` |
| **Owner** | Paulo Guilherme Alencar |
| **Caveats** | (1) Includes all transaction natures (compra e venda, doação, arrematação, etc.) unless the Engineer applies a natureza_transacao filter in Silver — confirm with model_spec.md that no nature filter was applied. Per the current model spec, no such filter exists; all qualifying transactions are counted. (2) Duplicates in the source XLSX (same property, date, value across two sheets) are deduplicated by the MD5 surrogate key in Silver — the count reflects deduplicated records only. |

---

## Section 2 — Dashboard Design

### Technology Stack

- **Runtime:** Streamlit >= 1.32.x
- **Charting:** Plotly (bundled with Streamlit; interactive hover, zoom, pan)
- **Storage access:** DuckDB in read-only mode via `@st.cache_resource` connection
- **Query caching:** `@st.cache_data(ttl=3600)` on all data-fetching functions
- **No other BI tool is used or assumed**

### Month Display Convention

All `month_year` strings (format: `YYYY-MM`) are converted to Portuguese month names before display:

```
2026-01 → Janeiro/2026
2026-02 → Fevereiro/2026
2026-03 → Março/2026
```

A `format_month_pt(month_year: str) -> str` helper function performs this mapping. All axis labels, table headers, and filter labels use the Portuguese form.

### Numeric Formatting

| Value type | Format |
|---|---|
| BRL prices | `R$ {:,.0f}` (comma thousands separator, no decimals) |
| BRL price/m² | `R$ {:,.0f}/m²` |
| MoM change | `+X.XX%` with explicit sign; negative in red, positive in green, NULL as `—` |
| Transaction count | Integer, comma-separated for thousands |

---

### Sidebar — Global Controls

The sidebar is always visible and applies globally across all three sections.

**Controls:**

1. **Month Range Selector** (`st.select_slider`)
   - Label: "Período de análise"
   - Values: all distinct `month_year` values from `gold_itbi_monthly_summary`, displayed as Portuguese month names
   - Returns: (start_month, end_month) tuple in YYYY-MM format for SQL filtering
   - Default: full available range (currently JAN-2026 to MAR-2026)

2. **Minimum Transaction Threshold Toggle** (`st.toggle`)
   - Label: "Ocultar bairros com menos de N transações/mês"
   - Default: ON (hide bairros with transaction_count < 3)
   - When ON: appends `AND transaction_count >= 3` to neighborhood queries
   - When OFF: all bairros shown; a warning badge is displayed on low-volume rows

3. **Data freshness notice** (`st.caption`)
   - Displays: "Dados atualizados em: [max ingested_at from bronze] — Fonte: Prefeitura de SP (ITBI declarado)"
   - Reminds the user that values are self-declared and may lag actual transfers

---

### Section A — City-wide Trends

**Purpose:** Answer business question 1 — how have building transaction prices evolved month-over-month in 2026 across all of São Paulo?

**Source table:** `gold_itbi_monthly_summary`

**Columns queried:**
```sql
SELECT month_year, transaction_count, total_value_brl,
       kpi_median_price, kpi_median_price_per_m2, avg_price_per_m2
FROM gold_itbi_monthly_summary
WHERE month_year BETWEEN :start_month AND :end_month
ORDER BY month_year
```

#### Chart A1 — Median Transaction Price Evolution (Plotly Line Chart)

- **Chart type:** `plotly.graph_objects.Figure` with `go.Scatter(mode='lines+markers')`
- **Why this type:** A line chart with markers is ideal for showing a continuous time series with a small number of data points (3 months). It communicates trend direction immediately and supports hover for exact values. A bar chart would work but implies discrete categories rather than temporal flow.
- **X-axis:** Portuguese month names (Janeiro/2026, Fevereiro/2026, Março/2026)
- **Y-axis:** Median Transaction Price in BRL (`kpi_median_price`)
- **Secondary Y-axis (right):** Transaction Volume (`transaction_count`) as a bar (`go.Bar`, opacity 0.3, grey)
- **Hover template:** "Mês: {month_pt}<br>Mediana: R$ {kpi_median_price:,.0f}<br>Transações: {transaction_count:,}"
- **Annotation:** MoM % change labeled directly above each data point (calculated in Python from consecutive rows; displayed as `—` for the first month)
- **Title:** "Evolução da Mediana de Preço de Transação — São Paulo (2026)"
- **Interaction:** Hover reveals exact values; zoom/pan enabled; legend toggle hides/shows volume bars

#### Chart A2 — Median Price per m² Evolution (Plotly Line Chart with area fill)

- **Chart type:** `go.Scatter(mode='lines+markers', fill='tozeroy')` with semi-transparent fill
- **Why this type:** The area fill visually reinforces the magnitude of the price/m² level relative to zero, making it easy to see not just the trend but the absolute scale. Used alongside Chart A1 to compare appreciation in price vs. appreciation in per-m² terms (which removes unit-size composition effects).
- **X-axis:** Portuguese month names
- **Y-axis:** Median Price per m² (`kpi_median_price_per_m2`) in BRL/m²
- **Hover template:** "Mês: {month_pt}<br>Mediana/m²: R$ {kpi_median_price_per_m2:,.0f}/m²"
- **MoM annotation:** Same treatment as Chart A1
- **Title:** "Evolução da Mediana de Preço por m² — São Paulo (2026)"

#### Metric Row (between charts)

Three `st.metric` cards displayed side by side using `st.columns(3)`:

| Card | Value | Delta |
|---|---|---|
| Mediana de Preço (último mês) | `kpi_median_price` for max(month_year) | MoM % change vs. prior month, green/red |
| Mediana Preço/m² (último mês) | `kpi_median_price_per_m2` for max(month_year) | MoM % change, green/red |
| Total de Transações (período) | sum of `transaction_count` across selected range | — |

---

### Section B — Neighborhood Ranking

**Purpose:** Answer business question 2 — which neighborhoods have seen the highest price appreciation?

**Source table:** `gold_itbi_neighborhood_ranking`

**Columns queried:**
```sql
SELECT bairro_normalized, month_year, transaction_count,
       kpi_median_price, kpi_median_price_per_m2,
       kpi_mom_price_change_pct, kpi_mom_price_per_m2_change_pct
FROM gold_itbi_neighborhood_ranking
WHERE month_year BETWEEN :start_month AND :end_month
  AND (:min_tx_filter = FALSE OR transaction_count >= 3)
ORDER BY bairro_normalized, month_year
```

#### Chart B1 — Neighborhood Appreciation Bar Chart (Plotly Horizontal Bar)

- **Chart type:** `go.Bar(orientation='h')`, sorted descending by the selected appreciation metric
- **Why this type:** A horizontal bar chart is the standard for ranked comparisons with many categories (bairros). The horizontal orientation allows full neighborhood name display without label truncation. Color encoding (green → red gradient) adds an instant visual signal for top vs. bottom performers.
- **X-axis:** Appreciation metric (user-selectable: MoM Price Change % or MoM Price per m² Change %)
- **Y-axis:** `bairro_normalized` — top 20 bairros by default, expandable via a `st.number_input` ("Exibir top N bairros", min=5, max=100, default=20)
- **Month selector (local filter):** `st.selectbox` — select which month's MoM change to display; defaults to the most recent month with non-NULL MoM (i.e., not the first month)
- **Color scale:** `px.colors.diverging.RdYlGn` — red for negative, yellow for zero, green for positive
- **NULL handling:** Bairros with NULL MoM (first month) are excluded from this chart — a `st.info` note explains "Primeiro mês excluído do ranking (sem base de comparação)"
- **Title:** "Top {N} Bairros por Valorização — {month_pt}"
- **Hover:** "Bairro: {bairro}<br>Valorização MoM: {+X.XX%}<br>Mediana: R$ {kpi_median_price:,.0f}<br>Transações: {transaction_count:,}"

#### Table B2 — Full Neighborhood Ranking Table (Styled DataFrame)

- **Component:** `st.dataframe` with Pandas `Styler` for conditional formatting
- **Why this type:** An interactive, sortable, filterable table gives the user full control over ranking by any column. Plotly charts support only one sort dimension at a time; the table lets the stakeholder pivot by price, volume, or MoM change in one click.
- **Columns displayed:**

| Display label | Source column | Format |
|---|---|---|
| Bairro | bairro_normalized | — |
| Mês | month_year | Portuguese name |
| Transações | transaction_count | Integer |
| Mediana Preço | kpi_median_price | R$ {:,.0f} |
| Mediana Preço/m² | kpi_median_price_per_m2 | R$ {:,.0f}/m² |
| Variação MoM (Preço) | kpi_mom_price_change_pct | +X.XX% / — |
| Variação MoM (Preço/m²) | kpi_mom_price_per_m2_change_pct | +X.XX% / — |

- **Conditional formatting:**
  - MoM change columns: green background for positive, red background for negative, grey italic for NULL (displayed as `—`)
  - Rows where transaction_count < 3 and toggle is OFF: light yellow background with a warning icon in the Bairro cell
- **Local filter:** `st.multiselect("Filtrar por bairro", ...)` — allows the user to select specific neighborhoods to inspect across all months
- **Sort:** Streamlit's built-in column sort is sufficient; default sort by `kpi_mom_price_change_pct` DESC for the latest month

---

### Section C — Price per m² Drill-down

**Purpose:** Answer business question 3 — what is the price per m² trend by area and property type?

**Source table:** `gold_itbi_price_per_m2`

**Columns queried:**
```sql
SELECT bairro_normalized, uso_desc, month_year,
       transaction_count, kpi_median_price_per_m2, kpi_avg_price_per_m2
FROM gold_itbi_price_per_m2
WHERE month_year BETWEEN :start_month AND :end_month
  AND (:min_tx_filter = FALSE OR transaction_count >= 3)
  AND (:selected_bairros IS NULL OR bairro_normalized = ANY(:selected_bairros))
  AND (:selected_uso IS NULL OR uso_desc = ANY(:selected_uso))
ORDER BY bairro_normalized, uso_desc, month_year
```

#### Local Filters (Section C)

1. **Bairro multiselect** (`st.multiselect`): "Selecionar bairros para análise" — populated from distinct `bairro_normalized` values in `gold_itbi_price_per_m2`. Default: empty (shows city-wide aggregation when empty). Maximum recommended selection: 5 bairros for readable chart.

2. **Property type multiselect** (`st.multiselect`): "Tipo de uso" — populated from distinct `uso_desc` values. Values where `uso_desc = 'UNKNOWN'` are displayed as "Tipo não identificado" (per caveat 6). Default: all types shown.

#### Chart C1 — Price per m² Trend by Neighborhood and Property Type (Plotly Line Chart, multi-series)

- **Chart type:** `go.Scatter(mode='lines+markers')` — one line per `(bairro_normalized, uso_desc)` combination
- **Why this type:** Multiple time series on one chart allows direct visual comparison of how different neighborhood-type segments evolve. This is more informative than separate charts when comparing 2-5 bairros. If the user selects more than 5 bairros, a `st.warning` advises reducing selection for readability.
- **X-axis:** Portuguese month names (time dimension)
- **Y-axis:** `kpi_median_price_per_m2` in BRL/m²
- **Line color:** Automatically assigned by Plotly color sequence, one color per bairro; line style (solid/dashed/dotted) differentiates uso_desc within the same bairro
- **Hover:** "Bairro: {bairro}<br>Tipo: {uso_desc}<br>Mês: {month_pt}<br>Mediana/m²: R$ {kpi_median_price_per_m2:,.0f}/m²<br>Transações: {transaction_count:,}"
- **Empty state:** If no bairro is selected, display the top 3 bairros by transaction volume as a default selection with a `st.info` note
- **NULL handling:** If `kpi_median_price_per_m2` is NULL for a (bairro, uso_desc, month) combination — because all transactions in that segment were land-only — the line has a gap at that month; a `st.caption` explains "Lacunas indicam meses sem transações com área construída informada"

#### Chart C2 — Price per m² by Property Type, Latest Month (Plotly Box-like Bar with error bars)

- **Chart type:** `go.Bar` grouped by `uso_desc`, showing median with an overlay of mean (`kpi_avg_price_per_m2`) as a scatter marker
- **Why this type:** A grouped bar with a mean overlay communicates both central tendency and skew direction (mean above median = right-skewed, mean below = left-skewed) without requiring raw transaction data in the dashboard layer. This is the most compact chart that answers "which property type commands the highest price/m² in the selected bairros?"
- **X-axis:** `uso_desc` (property type) — "Tipo não identificado" for UNKNOWN
- **Y-axis:** BRL/m² (median bar + mean marker)
- **Month:** Fixed to the latest available month in the selected range
- **Grouping:** If multiple bairros are selected, group bars by uso_desc and use bairro as the color dimension
- **Title:** "Preço Mediano por m² por Tipo de Uso — {latest_month_pt}"

---

### Full Layout Narrative

```
┌─ Sidebar ─────────────────────────────────┐  ┌─ Main area ────────────────────────────────────────────┐
│ Período de análise: [JAN/2026 ↔ MAR/2026] │  │ st.title("Dashboard ITBI São Paulo — 2026")            │
│ Ocultar bairros < 3 tx/mês: [ON]          │  │ st.caption("Dados: Prefeitura de SP · Valores declarados")│
│                                           │  │                                                         │
│ Dados atualizados em: 2026-04-01          │  │ ═══ A. Evolução Citywide ════════════════════════════   │
│ Fonte: Prefeitura de SP (ITBI declarado)  │  │ [st.metric] Mediana  [st.metric] /m²  [st.metric] Vol  │
│                                           │  │ [Chart A1 — Linha: Mediana Preço + Volume]              │
│                                           │  │ [Chart A2 — Área: Mediana Preço/m²]                    │
│                                           │  │                                                         │
│                                           │  │ ═══ B. Ranking de Bairros ═══════════════════════════  │
│                                           │  │ [selectbox: mês do ranking] [radio: métrica MoM]       │
│                                           │  │ [Chart B1 — Barras horizontais: Top N bairros]         │
│                                           │  │ [multiselect: filtrar bairro] [toggle: min_tx]         │
│                                           │  │ [Table B2 — DataFrame com formatação condicional]      │
│                                           │  │                                                         │
│                                           │  │ ═══ C. Drill-down Preço/m² ══════════════════════════  │
│                                           │  │ [multiselect: bairros] [multiselect: tipo de uso]      │
│                                           │  │ [Chart C1 — Linhas multi-série: /m² por bairro+tipo]   │
│                                           │  │ [Chart C2 — Barras agrupadas: /m² por tipo, último mês]│
└───────────────────────────────────────────┘  └────────────────────────────────────────────────────────┘
```

---

## Section 3 — Validation

### Reconciliation Check Results

**KPI 1 — Median Transaction Price**

Trace: `silver_itbi_transactions.valor_transacao` (all rows with `valor_transacao > 0`) → aggregated by `PERCENTILE_CONT(0.5)` in `gold_itbi_monthly_summary.kpi_median_price` and `gold_itbi_neighborhood_ranking.kpi_median_price`.

Verification method: For a spot-check month (e.g. Janeiro/2026), run:
```sql
SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY valor_transacao) AS check_median
FROM silver_itbi_transactions
WHERE month_year = '2026-01';
```
This must equal `gold_itbi_monthly_summary.kpi_median_price` for `month_year = '2026-01'`. The Gold model is a full-refresh `materialized: table` — no incremental drift is possible. dbt's `not_null` and `expression_is_true` tests on `kpi_median_price > 0` confirm the value was computed and is positive.

Dashboard display verification: The value shown in `st.metric` and Chart A1's first data point must exactly match the Gold table value. No rounding is applied at the Python/Streamlit layer (BRL format `{:,.0f}` rounds for display only, not for computation).

**KPI 2 — Median Price per m²**

Trace: `silver_itbi_transactions.price_per_m2` (computed as `ROUND(valor_transacao / area_construida_m2, 2)` for rows where `area_construida_m2 > 0`) → `PERCENTILE_CONT(0.5)` filter `WHERE price_per_m2 IS NOT NULL` → stored in Gold as `kpi_median_price_per_m2`.

Verification: Cross-check Gold monthly summary against Silver:
```sql
SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_per_m2)
       FILTER (WHERE price_per_m2 IS NOT NULL) AS check_median_m2
FROM silver_itbi_transactions
WHERE month_year = '2026-01';
```
Must equal `gold_itbi_monthly_summary.kpi_median_price_per_m2` for `month_year = '2026-01'`.

Additionally, `gold_itbi_price_per_m2.kpi_median_price_per_m2` at `(bairro, uso_desc, month)` must equal the analogous PERCENTILE_CONT computed from `silver_itbi_transactions` filtered to that `(bairro_normalized, uso_desc, month_year)` combination.

**KPI 3 — MoM Price Change**

Trace: Computed via `LAG(kpi_median_price) OVER (PARTITION BY bairro_normalized ORDER BY month_year)` in `gold_itbi_neighborhood_ranking`. The formula is:
`ROUND(((current - prev) / prev) * 100, 4)` — NULL when `prev IS NULL OR prev = 0`.

Verification: With 3 months of data:
- Janeiro/2026: `kpi_mom_price_change_pct` = NULL (no prior month) — confirmed by dbt: the LAG window for the first row returns NULL, and the CASE expression explicitly maps this to NULL.
- Fevereiro/2026: Compare manually — `(feb_median - jan_median) / jan_median * 100` must match the stored value rounded to 4 decimal places.
- Março/2026: Same check for `(mar_median - feb_median) / feb_median * 100`.

Dashboard: NULL values are displayed as `—` (em dash) in Table B2 and are excluded from Chart B1 with a visible `st.info` note. This prevents the user from misreading a missing first month as a 0% change.

**KPI 4 — MoM Price per m² Change**

Same LAG-based computation as KPI 3, applied to `kpi_median_price_per_m2`. Verification follows the same pattern. Additionally, this KPI can be NULL even for non-first months if `kpi_median_price_per_m2` was NULL (no built-area transactions in that neighborhood-month). The dashboard treats this case identically: display `—`, do not impute 0%.

**KPI 5 — Transaction Volume**

Trace: `COUNT(*)` from `silver_itbi_transactions` after `valor_transacao > 0` filter and `transaction_id` deduplication → stored as `transaction_count` in all three Gold tables.

Verification:
```sql
SELECT month_year, COUNT(*) AS silver_count
FROM silver_itbi_transactions
GROUP BY month_year
ORDER BY month_year;
```
Must match `gold_itbi_monthly_summary.transaction_count` exactly for each month. If they differ, a re-run of `dbt run` will correct any stale Gold table state (since all models are `materialized: table` — full refresh on every run).

---

### Filter and Drilldown Test Evidence

**Month Range Selector**

- Test 1: Select Janeiro/2026 only. Expect: Chart A1 shows a single point (no line); Chart B1 shows all bairros with NULL MoM (filter note appears); Table B2 shows one row per bairro for January only.
- Test 2: Select all 3 months. Expect: Charts show 3 data points; MoM values appear for February and March; January MoM shown as `—`.
- Test 3: Select Fevereiro to Março only. Expect: Chart A1 shows 2 points; MoM change for Março is visible; Fevereiro now appears as the "first" month in the display range — but the MoM value stored in Gold still reflects the Jan→Feb change, so it is shown correctly. Note: the Gold table stores absolute MoM, not relative to the filter window — the filter does not retroactively set Fevereiro's MoM to NULL.

**Minimum Transaction Threshold Toggle**

- Test ON (default): Neighborhoods with transaction_count < 3 in a given month are excluded from all neighborhood charts and tables. Total count of displayed bairros decreases.
- Test OFF: All bairros visible. Rows with transaction_count < 3 receive a yellow background in Table B2 and a warning tooltip: "Menos de 3 transações — KPI com alta variabilidade".

**Property Type Multiselect (Section C)**

- Select "APARTAMENTO" only: Chart C1 shows lines only for the APARTAMENTO uso_desc. Chart C2 shows only one bar group.
- Select "UNKNOWN" / "Tipo não identificado": Data is shown normally; the label in the chart and table displays "Tipo não identificado" — never the raw string "UNKNOWN".
- Select all types (default): All lines shown in Chart C1; Chart C2 shows all property types side by side.

**Bairro Multiselect (Section C)**

- Select 0 bairros: Dashboard defaults to top 3 by transaction_count for the selected period. A `st.info` box explains: "Nenhum bairro selecionado — exibindo os 3 com maior volume de transações".
- Select 1 bairro: Chart C1 shows separate lines per uso_desc for that bairro. Chart C2 shows bars for all uso_desc types in that bairro for the latest month.
- Select > 5 bairros: `st.warning` appears: "Selecione até 5 bairros para melhor legibilidade". The chart still renders but may be visually crowded.

---

### Edge Case Behavior

**First-month NULL MoM (January 2026)**

- In Table B2: `kpi_mom_price_change_pct` column shows `—` (em dash, not "0%", not "None", not blank). Implemented via pandas `.fillna('—')` applied after formatting.
- In Chart B1: January is excluded from the ranking chart when it is selected as the target month, because all MoM values are NULL for January. The chart displays an explanatory note instead of an empty chart: "Nenhum dado de variação MoM disponível para o primeiro mês".
- In `st.metric` delta: For the first month, the delta is hidden (`delta=None`) rather than showing 0% or an error.

**Low-volume Bairros (< 3 transactions/month)**

- When toggle is ON: SQL query includes `AND transaction_count >= 3`; these bairros are fully hidden.
- When toggle is OFF: These bairros appear with yellow background in Table B2. Their KPIs are shown but a small warning icon (⚠) is prepended to the bairro name. Chart B1 includes them but they are shown with reduced opacity (0.5) to visually signal lower reliability.
- The threshold is set at 3 per the model_spec decision; it is not user-configurable in v1 (the toggle is on/off, not a numeric input).

**Unknown uso_desc ('UNKNOWN')**

- All display labels replace `'UNKNOWN'` with `"Tipo não identificado"`. This is applied at the Python query-result processing step (`df['uso_desc'].replace('UNKNOWN', 'Tipo não identificado')`), not in SQL, to keep Gold tables consistent with the model spec.
- This segment is included in all charts and tables by default. The user can deselect it in the property type multiselect.

**All-NULL price_per_m2 for a Bairro**

- If a bairro has zero transactions with area_construida_m2 > 0 (all land-only), its row does not exist in `gold_itbi_price_per_m2` (filtered at the model level by `WHERE price_per_m2 IS NOT NULL`). It will therefore not appear in Section C charts.
- In Section B's Table B2, its `kpi_median_price_per_m2` and `kpi_mom_price_per_m2_change_pct` will be NULL; displayed as `—`.
- No error is raised; the dashboard handles missing neighborhood-type combinations gracefully by simply having no row for that segment.

**Empty Query Result (all filters applied, no data)**

- If the combination of month range + bairro + uso_desc filters returns zero rows: each chart component displays `st.info("Nenhum dado encontrado para os filtros selecionados.")` rather than an empty Plotly chart (which would show an unhelpful blank area).

---

### Known Interpretation Limits

1. **3-month window is statistically thin.** With only JAN-MAR 2026, any MoM comparison represents a single data point. Trend lines with 2 MoM values (Feb vs Jan, Mar vs Feb) are directional signals only — they should not be interpreted as confirmed trends.
2. **Self-declared values.** Declared ITBI values may be underreported. The dashboard uses median to reduce outlier sensitivity but cannot correct for systematic under-declaration.
3. **Declaration lag.** ITBI is filed after the transaction is registered at the cartório. A March declaration may reflect a January or February transfer. This lag is structural in the source data and cannot be corrected at any pipeline layer.
4. **Neighborhood normalization is heuristic.** The `normalize_bairro` macro applies a deterministic but incomplete normalization. Two bairros that the human recognizes as the same place may remain split in the data if the source spellings were too different to match by the current expansion rules.
5. **No comparator dataset.** The dashboard cannot compare ITBI prices to market listing prices or FIPE indices — it only reflects declared ITBI values.

---

## Section 4 — Decision Narrative

### Key Insights Available from JAN-MAR 2026

**1. Overall market direction.** Chart A1 provides an objective reading of whether São Paulo's median transaction price is increasing, decreasing, or stable across the first quarter of 2026. Even with three data points, a consistent directional trend (two consecutive increases or two consecutive decreases) is a meaningful signal for investment timing.

**2. Neighborhood divergence.** In any real estate market, citywide trends mask significant neighborhood-level divergence. Chart B1 will surface which bairros are outperforming the city median — candidates for deeper acquisition due diligence — and which are underperforming or declining, indicating potential oversupply or declining demand in that micro-market.

**3. Property type premium.** Section C's use-type analysis answers whether APARTAMENTO, RESIDENCIA, or COMERCIAL transactions are appreciating fastest in the target neighborhoods. This informs which property type the stakeholder should prioritize within a given bairro.

**4. Volume vs. price signal.** The combined view of transaction_count and kpi_median_price in Chart A1 allows the user to distinguish between price appreciation driven by genuine demand (high volume + high price) and price appreciation driven by a thin market (very few transactions at atypically high values).

### Recommended Actions for the Stakeholder

1. **Identify top 5 bairros by MoM appreciation in March 2026** using Chart B1. Cross-reference these with transaction_count — only trust the ranking for bairros with >= 10 transactions/month.
2. **Check price/m² trend in those bairros** in Section C, filtered by APARTAMENTO (or the relevant property type for the intended investment).
3. **Monitor for a second quarter of data** — a single MoM change is insufficient for investment decisions. The pipeline auto-detects new monthly sheets; adding April 2026 data requires only a re-run of `make pipeline`.
4. **Apply the minimum-transaction toggle conservatively** — for investment research, consider raising the mental threshold to 5-10 transactions before trusting a neighborhood's KPI.
5. **Cross-validate outliers** — any bairro showing > 15% MoM appreciation on < 10 transactions should be manually inspected in the raw ITBI data to rule out a single large commercial transaction distorting the median.

### Confidence Level and Caveats on the 3-Month Window

**Confidence: LOW to MODERATE for trend identification; MODERATE for absolute price benchmarking.**

- For trend identification: 2 MoM observations per neighborhood is the absolute minimum for directionality. Statistical confidence in the trend requires at least 4-6 months. The JAN-MAR window is useful for identifying *candidate* neighborhoods, not for confirming trends.
- For absolute price benchmarking: The median price and price/m² figures are directly derived from declared transaction values in the official ITBI registry. For the purpose of understanding the current price level in a neighborhood, these figures are reliable — subject to the self-declaration caveat.
- For market timing: The 3-month window can identify whether Q1 2026 is overall an appreciating or depreciating market, which is useful context for deal pricing. It cannot identify cyclical patterns or seasonal effects (which require at least 12 months of history).

The dashboard is designed to grow in analytical power as more months are added. The architecture supports this — no code changes are needed to add new months.
