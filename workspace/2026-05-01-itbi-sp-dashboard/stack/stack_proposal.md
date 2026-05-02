# Stack Proposal — 2026-05-01-itbi-sp-dashboard

**Request:** ITBI SP Real Estate Price Dashboard  
**Prepared by:** Data Architect (Mode A — Stack Proposal)  
**Date:** 2026-05-01  
**Status:** Proposed — Awaiting Engineer Validation

---

## Project Context Summary

| Dimension | Value |
|---|---|
| Deployment | Local machine (macOS), no cloud infra |
| Budget | Cost matters a lot — open-source only |
| Team skills | Python, SQL, dbt, Streamlit |
| Source | Single XLSX file, ~50K rows (JAN–MAR 2026), growing monthly by ~15–20K rows |
| Update trigger | Manual, on demand when new monthly sheet is added |
| Privacy constraint | Exclude fields marked personal/fiscal-secrecy per LEGENDA sheet |
| SLA | None — best-effort, local re-run on demand |

---

## Confirmed Stack

### 1. Storage — DuckDB

**Recommendation:** DuckDB

**Rationale:**
- Single-file embedded database — zero server setup, zero ops overhead, runs entirely in-process.
- Native support for reading XLSX/CSV via extensions (`spatial`, `excel`), and excellent Parquet/Arrow interop.
- SQL-first: dbt-duckdb adapter allows dbt to target DuckDB directly, keeping the entire Bronze → Silver → Gold transformation chain inside SQL without any extra runtime.
- At the project's volume (~50K–200K rows across 12 months at full year), DuckDB executes analytical queries in milliseconds without tuning.
- Persistent `.duckdb` file can live inside the workspace directory, making the entire project self-contained in a single repo folder.

**Main Alternative: PostgreSQL**
- Requires running a server daemon (even via Docker), which adds operational complexity on a local machine and violates the "zero infrastructure" spirit of this project.
- No performance advantage at this data volume; DuckDB is faster for OLAP-style queries at small-to-medium scale.
- Rejected for this project.

**Assumptions:**
- Final DuckDB file size will stay well under 1 GB at full 2026 scope (~12 months × ~17K rows average).
- The `.duckdb` file will be stored at `workspace/2026-05-01-itbi-sp-dashboard/build/itbi_sp.duckdb` (or equivalent path set in dbt profile).

---

### 2. Transform — dbt core + dbt-duckdb adapter

**Recommendation:** dbt core (open-source, self-hosted) with the `dbt-duckdb` adapter

**Rationale:**
- Team already knows dbt — zero learning curve, immediate productivity.
- dbt models enforce the Bronze → Silver → Gold medallion architecture with naming conventions (`bronze_itbi_transactions`, `silver_itbi_transactions`, `gold_itbi_*`).
- Auto-detection of new monthly sheets can be handled by a single Python macro or a `sources.yml` + seed approach at the Bronze layer — the pattern matching (`[A-Z]{3}-\d{4}`) is resolved at runtime, so adding a new sheet requires no model changes.
- dbt tests (`not_null`, `unique`, `accepted_values`) provide built-in data quality validation at each layer transition.
- `dbt-duckdb` is the official DuckDB adapter for dbt core; it is open-source and well-maintained.

**Main Alternative: Polars or Pandas (pure Python transforms)**
- Viable for a project this size, but would bypass the SQL/dbt skills the team already has.
- No built-in test framework, no lineage graph, no documentation generation.
- Would require writing custom Python scripts for each transformation that dbt models would handle declaratively.
- Rejected in favor of dbt to maximize maintainability and team familiarity.

**Assumptions:**
- The XLSX ingestion step (reading all month-named sheets) will be handled by a small Python ingestion script that writes raw data into DuckDB Bronze tables before dbt runs. dbt will handle Bronze → Silver → Gold only.
- Sheet auto-detection pattern: `^[A-Z]{3}-\d{4}$` (e.g., `JAN-2026`, `FEV-2026`). This regex is applied by the ingestion script, not dbt.

---

### 3. Orchestration — None (manual invocation via shell script or Makefile)

**Recommendation:** No orchestrator — a single `Makefile` or `run_pipeline.sh` script

**Rationale:**
- Update frequency is manual and on-demand — no schedule, no SLA, no dependency graph beyond "ingest then transform then serve."
- All approved orchestrators (Airflow, Dagster, Prefect, Mage) carry significant installation and daemon overhead for a pipeline that runs perhaps once per month.
- A `Makefile` with targets (`make ingest`, `make transform`, `make serve`) provides the same sequential execution with zero overhead and is understandable by any developer.
- The pipeline has exactly two steps: (1) Python ingestion script → DuckDB, (2) `dbt run` + `dbt test`. A Makefile or shell script handles this trivially.

**Main Alternative: Dagster (open-source)**
- The most developer-friendly orchestrator in the approved list; its asset-based model maps well to medallion layers.
- However, it requires a running daemon and web server, which is disproportionate overhead for a monthly-manual pipeline with one user.
- Dagster is the recommended upgrade path if this pipeline ever needs scheduling, alerting, or multi-step dependency management.
- Rejected for the current scope; noted as the natural upgrade if complexity grows.

**Assumptions:**
- The pipeline will be invoked manually by the user (Paulo) when a new monthly sheet is dropped.
- No retry logic or failure alerting is required at launch.

---

### 4. BI / Visualization — Streamlit

**Recommendation:** Streamlit (explicitly specified by the user in the intake)

**Rationale:**
- Directly specified in the intake as the preferred BI layer — no decision needed.
- Team knows Python, so Streamlit charts are written in familiar code rather than a drag-and-drop UI.
- Connects natively to DuckDB via `duckdb` Python package — queries run in-process, no network hop.
- Supports the required chart types (line charts for MoM evolution, bar/ranking charts for neighborhood appreciation, area/scatter for price per m² trends).
- Lightweight: runs as a local web server (`streamlit run app.py`), no database server, no separate web server.

**Main Alternative: Apache Superset**
- More powerful for self-service SQL exploration, but requires a running web server + metadata database (SQLite or PostgreSQL) and is significantly heavier to set up locally.
- Overkill for a single-user dashboard with a defined set of 3+ charts.
- Rejected in favor of Streamlit's simplicity and the team's existing familiarity.

**Assumptions:**
- Dashboard will be served locally via `streamlit run` — no deployment to a remote server required.
- Plotly (via `plotly` or `streamlit`'s native chart functions) will be used for interactive charts; Plotly is a Python library, not a standalone BI tool, and does not require separate approval.

---

### 5. Data Quality — dbt tests

**Recommendation:** dbt tests (built-in to dbt core)

**Rationale:**
- Already included in the dbt core installation — zero additional dependencies.
- Covers the key quality checks needed: `not_null` on transaction amount and reference date, `unique` on transaction IDs, `accepted_values` for property type codes.
- Tests run automatically as part of `dbt test` after `dbt run`, ensuring data quality is validated at every layer before the dashboard reads Gold tables.
- Results are visible in `target/run_results.json` and can be inspected with standard tooling.

**Main Alternative: Great Expectations**
- Significantly more powerful for complex data profiling and expectation suites.
- However, it adds substantial setup complexity (data context, checkpoints, data docs) that is disproportionate to the project's quality requirements.
- The ITBI dataset is structured public data with a well-defined schema — dbt's built-in tests are sufficient.
- Rejected for current scope; Great Expectations is the natural upgrade if quality requirements become more complex (e.g., cross-sheet consistency checks, distribution-based anomaly detection).

**Assumptions:**
- Privacy field exclusion (fields marked personal/fiscal-secrecy per LEGENDA) will be enforced at the Bronze ingestion step by the Python script — they will never be written to DuckDB. dbt tests will confirm these columns are absent from Silver/Gold models.

---

## Stack Summary Table

| Category | Chosen Tool | Version Guidance |
|---|---|---|
| Storage | DuckDB | >= 0.10.x (latest stable) |
| Transform | dbt core + dbt-duckdb | dbt-core >= 1.7, dbt-duckdb >= 1.7 |
| Orchestration | None (Makefile / shell script) | N/A |
| BI / Viz | Streamlit | >= 1.32.x (latest stable) |
| Data Quality | dbt tests (built-in) | Included in dbt-core |
| Data Ingestion | Python + openpyxl + pandas | pandas >= 2.x, openpyxl >= 3.x |

> **Note on ingestion libraries:** `pandas` and `openpyxl` are used exclusively in the ingestion script (XLSX reading). `pandas` is on the approved Transform list. `openpyxl` is a Python standard-ecosystem XLSX parser (MIT license); it is not a standalone tool requiring a separate approval — it is a library dependency, not a platform component. If the Engineer considers it a material addition, it should be flagged for human review.

---

## Architecture Flow

```
data/GUIAS DE ITBI PAGAS (2).xlsx
        |
        v
[Python ingestion script]
  - Detects all sheets matching ^[A-Z]{3}-\d{4}$
  - Excludes privacy fields (from LEGENDA)
  - Writes raw rows to DuckDB: bronze_itbi_transactions
        |
        v
[dbt run + dbt test]
  bronze_itbi_transactions
        → silver_itbi_transactions   (typing, dedup, standardization)
        → gold_itbi_monthly_summary  (MoM price evolution)
        → gold_itbi_neighborhood_ranking  (appreciation by bairro)
        → gold_itbi_price_per_m2    (price/m² by area, type, month)
        |
        v
[Streamlit app]
  - Queries Gold tables via DuckDB Python connector
  - Renders: line chart (MoM), bar chart (ranking), scatter/heatmap (price/m²)
  - Filters by property type, neighborhood, month range
```

---

## Assumptions Log

| ID | Assumption | Impact if Wrong |
|---|---|---|
| A1 | Total annual volume stays under 250K rows (12 × ~20K avg) | No impact on tool choice at 10× this volume; DuckDB handles millions of rows on a laptop |
| A2 | XLSX file structure is consistent across sheets (same columns in same order) | Ingestion script will need per-sheet schema negotiation if columns differ — Engineer must validate |
| A3 | Privacy field list from LEGENDA sheet is stable (no new protected fields added mid-year) | If LEGENDA changes, ingestion script exclusion list must be updated — a code change would be required |
| A4 | `openpyxl` is treated as a library dependency, not a platform component, and does not require separate approval | If the human requires formal approval for all Python packages, openpyxl must be added to a pending approval list |
| A5 | Plotly is used as the charting library inside Streamlit (not a separate BI platform) | If team prefers Altair or Matplotlib, chart implementation changes but stack does not |
| A6 | The DuckDB `.duckdb` file is treated as a build artifact, not checked into git | If the user wants the database in version control, a different persistence strategy is needed |

---

## Open Questions for the Engineer

| # | Question | Why It Matters |
|---|---|---|
| OQ-1 | Are all monthly sheets in the XLSX guaranteed to have the same column names and order? If not, which columns vary? | Determines whether the ingestion script can use a single schema or must handle per-sheet schema inference |
| OQ-2 | What is the exact list of columns flagged as personal/fiscal-secrecy in the LEGENDA sheet? Can you extract and confirm the exclusion list before writing the ingestion script? | Privacy compliance — these fields must never reach DuckDB |
| OQ-3 | Is `GUIA_DE_ITBI` (or equivalent) a reliable unique identifier per transaction across all sheets, or can duplicates appear within the same sheet or across months? | Determines dedup strategy in the Silver layer |
| OQ-4 | What column represents the neighborhood (`bairro`)? Is it a free-text field, a code, or a standardized name? What is the cardinality (estimated number of unique bairros)? | Determines whether a neighborhood dimension table / standardization step is needed in Silver |
| OQ-5 | Is the `area_m2` (built area or land area) a single column or computed from multiple columns? Are there known null rates for this field? | Determines how price/m² is computed and whether imputation is needed |
| OQ-6 | Will the XLSX file always be located at `data/GUIAS DE ITBI PAGAS (2).xlsx` relative to the project root, or could the path change? | Determines whether the file path should be hardcoded, configurable via `.env`, or discovered dynamically |
| OQ-7 | Is there a `property_type` (use/standard) column and what are its valid values? Does it correspond to the `LEGENDA` sheet's lookup table? | Drives the `accepted_values` dbt test and the dashboard filter by property type |
| OQ-8 | The ingestion script uses `pandas` + `openpyxl` for XLSX reading. Are there any concerns about adding these as dependencies, or should we use an alternative (e.g., `polars` with its built-in Excel reader)? | Affects `requirements.txt` and venv setup |

---

## Proposed Additions Requiring Human Approval

None. All components in the confirmed stack are on the approved list in `standards/tech_constraints.md`. The ingestion libraries (`pandas`, `openpyxl`) are standard Python ecosystem packages used as dependencies, not platform tools.

If the human considers `openpyxl` a material addition requiring explicit approval, it should be noted here before the Engineer proceeds.

---

## Next Steps (for Coordinator)

Upon human approval of this stack proposal:
1. Dispatch the **Data Engineer** in Mode A (Pipeline Build) with this stack proposal and the intake.md as inputs.
2. Engineer must produce `build/pipeline_spec.md` with virtual environment setup, `requirements.txt`, ingestion script spec, and dbt project structure.
3. Gate B must be evaluated before the Engineer writes any code.
