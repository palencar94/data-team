# Stack Validation — 2026-05-01-itbi-sp-dashboard

**Prepared by:** Data Engineer (Stack Validation Mode)  
**Date:** 2026-05-01  
**Input:** stack_proposal.md (Architect, 2026-05-01)  
**Status:** Validation Complete — Agreed with Modifications

---

## Summary Verdict

The Architect's proposed stack is **feasible and approved with minor modifications**. All components are on the approved tool list. One counter-proposal is raised for ingestion libraries (OQ-8). All other components are accepted as proposed. No blockers.

---

## Component-by-Component Assessment

---

### 1. Storage — DuckDB

**Verdict: AGREE — feasible as proposed.**

**Feasibility:** Confirmed. DuckDB runs fully embedded in Python, requires no daemon or server, and handles the projected volume (50K–250K rows) with query times in the low milliseconds on a modern MacBook. The single-file `.duckdb` artifact is portable and self-contained.

**Implementation notes:**
- DuckDB's Python package (`duckdb`) and dbt-duckdb both pin a compatible DuckDB version. Pin them together to avoid version conflicts. The `dbt-duckdb` adapter brings its own `duckdb` transitive dependency — do not install `duckdb` separately without checking the adapter's pinned version.
- The `.duckdb` file path should be set via an environment variable (e.g., `DUCKDB_PATH`) or in the dbt `profiles.yml` rather than hardcoded, to allow the workspace path to be relocated. The Architect's proposed build path (`workspace/2026-05-01-itbi-sp-dashboard/build/itbi_sp.duckdb`) is valid but must not be assumed static in scripts.
- The `.duckdb` file must be added to `.gitignore`. Checking a binary database file into git is destructive to the repo and will balloon history on every re-run.

**Risks:**
- Low. At this volume, DuckDB has no known failure modes on macOS.

---

### 2. Transform — dbt core + dbt-duckdb adapter

**Verdict: AGREE — feasible as proposed, with one version pin concern.**

**Feasibility:** Confirmed. The `dbt-duckdb` adapter is the official open-source adapter, actively maintained by the DuckDB community (MotherDuck). It supports all standard dbt-core features (models, tests, seeds, snapshots) against DuckDB.

**Implementation notes:**
- Version alignment is critical: `dbt-core` and `dbt-duckdb` must be pinned to compatible minor versions. The `dbt-duckdb` package pins `dbt-core` as a dependency, so specifying `dbt-duckdb>=1.8` in requirements and letting it pull the correct `dbt-core` version is the safest approach. Do not pin `dbt-core` independently unless you verify compatibility.
- The Architect's spec states that Bronze ingestion is handled by a Python script before dbt runs, and dbt handles Bronze → Silver → Gold. This is the correct division: the Python script writes raw data to a DuckDB table, dbt reads from it. This is the standard pattern for the dbt-duckdb adapter and is confirmed feasible.
- The XLSX sheet auto-detection (`^[A-Z]{3}-\d{4}$`) is applied by the Python ingestion script, not by dbt. This is the correct implementation boundary. dbt should not be responsible for file I/O.
- dbt profiles.yml will need to reference the `.duckdb` file path. For a local single-user setup, a `profiles.yml` in `~/.dbt/` or a project-local `profiles.yml` (with `--profiles-dir .`) are both valid. The project-local approach is preferred to keep the workspace self-contained.

**Risks:**
- Low. One known edge case: if dbt-duckdb and duckdb Python package versions conflict, DuckDB will throw a version mismatch error at connection time. This is resolved by letting `dbt-duckdb` control the `duckdb` transitive pin.

---

### 3. Orchestration — None (Makefile / shell script)

**Verdict: AGREE — correct choice for this scope.**

**Feasibility:** Confirmed. A Makefile with sequential targets is the appropriate level of orchestration for a pipeline that runs once a month on demand with no scheduling, no alerting, and no multi-user access.

**Implementation notes:**
- The proposed targets (`make ingest`, `make transform`, `make serve`) cover the three pipeline stages. A fourth target `make all` (or `make run`) chaining all three is recommended so the user can run the full pipeline with one command.
- The Makefile must activate the virtual environment before any Python or dbt command. This is typically done by calling commands as `.venv/bin/python` or `.venv/bin/dbt` rather than relying on shell activation, which does not persist across Makefile recipe lines.
- A `make test` target running `dbt test` should be included separately from `make transform` so quality checks can be run independently.
- Error handling: Makefile targets should use `.PHONY` declarations and `set -e` (or `&&` chaining) to ensure the pipeline halts on any step failure rather than silently proceeding.

**Risks:**
- Negligible. The only operational risk is a user running `make serve` before `make transform` completes. This can be mitigated by chaining dependencies in the Makefile (`transform: ingest`, `serve: transform`).

---

### 4. BI / Visualization — Streamlit

**Verdict: AGREE — feasible as proposed.**

**Feasibility:** Confirmed. Streamlit connects to DuckDB via the `duckdb` Python package natively. Since both the Streamlit app and the DuckDB file are on the same local machine, there is no connection complexity. Query results are returned as DataFrames and passed directly to Plotly or Streamlit's built-in chart functions.

**Implementation notes:**
- The Streamlit app should open the DuckDB connection in read-only mode (`duckdb.connect(path, read_only=True)`) when querying Gold tables. This prevents the app from accidentally locking the database during a pipeline re-run.
- The `.duckdb` file path must be configurable in the Streamlit app (via `st.secrets`, a `.env` file, or a `config.toml`) rather than hardcoded.
- Plotly is approved as a charting library inside Streamlit — it is a Python package, not a standalone BI platform. No separate approval needed.
- Streamlit's caching (`@st.cache_data`) should be used on DuckDB query functions to avoid re-querying on every UI interaction.

**Risks:**
- Low. One known issue: if the pipeline is running (`dbt run`) while the Streamlit app is connected to the same DuckDB file, DuckDB will raise a write-lock conflict. The read-only connection flag mitigates read-side conflicts. The user should be instructed to re-run the pipeline with the Streamlit app closed, or the Makefile target can document this.

---

### 5. Data Quality — dbt tests (built-in)

**Verdict: AGREE — sufficient for current scope.**

**Feasibility:** Confirmed. dbt's built-in generic tests (`not_null`, `unique`, `accepted_values`, `relationships`) are included in `dbt-core` with no additional installation. They run via `dbt test` and results are written to `target/run_results.json`.

**Implementation notes:**
- Privacy field exclusion (fields from LEGENDA) must be validated at two points: (1) the Python ingestion script must not write these columns to Bronze, and (2) a dbt test asserting these column names do not exist in Silver/Gold should be added. This is a schema test, achievable with `dbt-utils` (`expect_column_names_to_contain_only`) or a custom macro. Flag this as a build-time decision once OQ-2 is resolved.
- `dbt-utils` package adds useful cross-sheet consistency tests (e.g., `not_null` rate thresholds, row count comparisons across periods). If the cross-sheet consistency issue from OQ-1 materializes, `dbt-utils` is a low-overhead addition that remains within the dbt ecosystem.
- Test failures in `dbt test` should fail the Makefile pipeline (exit code 1). Ensure the Makefile `transform` target calls `dbt run && dbt test` so a test failure halts the pipeline before data reaches Gold.

**Risks:**
- Low. The only gap is cross-sheet schema consistency (OQ-1), which dbt built-in tests cannot catch at ingestion time. If columns vary across monthly sheets, this must be caught in the Python ingestion script with explicit validation before writing to Bronze.

---

### 6. Ingestion — Python + pandas + openpyxl

**Verdict: MODIFY — counter-proposal for ingestion library.**

**Feasibility of pandas + openpyxl:** Feasible, but not optimal. Both libraries work correctly for reading XLSX files with multiple sheets, and the regex sheet detection pattern is straightforward. However, `pandas` is listed on the approved Transform list, meaning its primary purpose is data transformation, and using it purely for XLSX I/O adds a heavy dependency (numpy, etc.) when a lighter option exists.

**Counter-proposal: `polars` with built-in Excel reader OR `openpyxl` alone**

Option A — `openpyxl` only (minimal):
- `openpyxl` can read XLSX sheets directly and return row data as Python dicts/lists without `pandas`.
- The ingestion script writes rows to DuckDB using the `duckdb` Python package's native `INSERT` or `executemany` interface.
- Eliminates `pandas` from the ingestion script entirely. DuckDB's Python API accepts native Python iterables directly.
- Best choice if the ingestion script is simple (no complex transformations before write).

Option B — `polars` (if light transforms needed at ingestion):
- `polars` is on the approved Transform list and has a built-in Excel reader (`polars.read_excel()`) that uses `xlsx2csv` or `fastexcel` as the backend.
- Faster than `pandas` for larger files, lower memory footprint.
- If the ingestion script needs to do any column casting, renaming, or filtering before writing to Bronze, `polars` is the preferred tool over `pandas`.
- Adds a dependency (`polars` + one of its Excel backends), but removes the `numpy` + `pandas` overhead.

**Recommendation:**
- If the ingestion script only reads sheets and writes raw rows to DuckDB with minimal logic: use **openpyxl alone** (no pandas).
- If the ingestion script needs type coercion, column filtering, or normalization before writing: use **polars** (replace pandas).
- Either option resolves OQ-8 with a leaner dependency tree.
- `pandas` is not blocked — if the team strongly prefers it for familiarity, it is approved and feasible. This is a preference-level modification, not a blocker.

**Final position:** Engineer recommends Option A (`openpyxl` only) for the ingestion script, with `polars` available if pre-write transforms are needed. `pandas` is approved as a fallback if the team disagrees.

---

## Open Questions — Engineer Responses (OQ-1 through OQ-8)

---

**OQ-1: Column schema consistency across sheets?**

Cannot confirm without inspecting the file. From a general engineering standpoint, Brazilian public ITBI data files from the São Paulo Prefeitura have historically maintained column consistency within a year but may add or remove columns between years. **Must verify before writing the ingestion script.** The script must include a schema validation step: read all sheet column lists, compare to a reference schema (derived from the first sheet), and raise an explicit error (not a silent skip) if any sheet deviates. The Architect's assumption A2 is reasonable but must be validated at build time.

**Implementation flag:** Add a `validate_schema_consistency()` function to the ingestion script that compares column sets across all detected sheets before any data is written to DuckDB. Fail fast on mismatch rather than attempting partial ingestion.

---

**OQ-2: Privacy field exclusion list from LEGENDA sheet?**

Cannot determine without reading the LEGENDA sheet. The LEGENDA sheet in São Paulo ITBI public data typically contains field descriptions and classification codes. Fields commonly marked as fiscal-secrecy or personal data include: CPF/CNPJ of buyer/seller, full residential address of parties, and cartório registration numbers. **The exact exclusion list must be extracted from the LEGENDA sheet before the ingestion script is written.** This is a hard dependency: the ingestion script cannot be finalized until this list is confirmed.

**Implementation flag:** The exclusion list should be stored as a constant in the ingestion script (or in a config file, e.g., `config/privacy_fields.yaml`) so it can be updated independently of the script logic if the LEGENDA changes in a future month.

---

**OQ-3: Reliable unique identifier per transaction?**

Cannot confirm without inspecting the data. ITBI records typically have a `NUMERO_GUIA` or `GUIA_DE_ITBI` field that serves as the payment guide number — this is generally unique per transaction within a year but should not be assumed unique across years. **Must verify by checking for duplicates in the first sheet before assuming it as a primary key.** The Silver layer dedup strategy should use a composite key (`guia_number + reference_date + sheet_month`) as a safe fallback if the guide number alone is not sufficient.

**Implementation flag:** The Silver model should use `row_number()` over `(guia_number, transaction_date, bairro)` as a tie-breaker dedup, not a bare `DISTINCT`. This prevents silent data loss if duplicates appear across months.

---

**OQ-4: Neighborhood field (bairro) type and cardinality?**

Cannot confirm cardinality without data inspection. São Paulo has approximately 96 official districts (`distritos`) but over 300 commonly referenced neighborhoods (`bairros`) in informal usage. ITBI data from the Prefeitura typically uses a `BAIRRO` free-text field that may contain inconsistent casing, accented vs. unaccented variants, and abbreviations. **Expect normalization to be needed in the Silver layer.**

**Implementation flag:** The Silver model should apply `UPPER(TRIM(bairro))` at minimum. A more robust approach is to build a `dim_bairro` seed or mapping table in dbt that maps raw `bairro` strings to canonical names. This should be flagged as a build decision once cardinality is confirmed from the actual data.

---

**OQ-5: area_m2 computation and null rate?**

Cannot determine without data inspection. ITBI records typically contain `AREA_CONSTRUIDA` (built area) and/or `AREA_TERRENO` (land area) as separate columns. Price per m² is typically computed against built area for apartment transactions and land area for lot transactions, depending on property type. **Null rate is unknown and must be profiled from the data.**

**Implementation flag:** The Silver model must handle nulls in area columns explicitly — either through a `COALESCE` fallback or by flagging zero/null-area records as `price_per_m2_unavailable` rather than dividing by zero. The Gold `gold_itbi_price_per_m2` model must filter out records with null or zero area before computing the metric.

---

**OQ-6: XLSX file path — hardcoded or configurable?**

**Recommendation: configurable via environment variable, with a documented default.**

The file path `data/GUIAS DE ITBI PAGAS (2).xlsx` has a space in the filename, which is a common source of issues in shell scripts and Makefiles. The ingestion script should accept the file path as an environment variable (`ITBI_SOURCE_FILE`) or a command-line argument, defaulting to the known path. The Makefile target should pass this variable explicitly.

**Implementation flag:** Add `ITBI_SOURCE_FILE ?= data/GUIAS DE ITBI PAGAS (2).xlsx` to the Makefile and pass it to the ingestion script. Ensure the path is properly quoted in all shell contexts. The `.env` file approach (loaded by the Makefile) is also acceptable.

---

**OQ-7: Property type valid values?**

Cannot determine valid values without inspecting the data or LEGENDA sheet. ITBI data typically includes a `TIPO_USO` (use type: residential, commercial, industrial) and/or `PADRAO_CONSTRUCAO` (construction standard: simple, normal, high). The `accepted_values` dbt test for this column requires the exact valid values — these must be derived from the LEGENDA sheet or from a `SELECT DISTINCT tipo_uso` query against the Bronze table after initial ingestion.

**Implementation flag:** Leave the `accepted_values` test for `property_type` as a placeholder in `schema.yml` until the first ingestion is run. Populate valid values from `SELECT DISTINCT` after Bronze is loaded. This is standard practice for first-load dbt setups.

---

**OQ-8: pandas + openpyxl vs. polars for XLSX reading?**

See component assessment in Section 6 above. Engineer counter-proposes `openpyxl` alone (no pandas) for ingestion, with `polars` as an alternative if pre-write transforms are needed. `pandas` is approved as a fallback. This is not a blocker — it is a dependency hygiene preference.

---

## Virtual Environment Strategy

### Python Version

**Recommended: Python 3.11.x**

Rationale:
- `dbt-core` 1.8.x and `dbt-duckdb` 1.8.x have full support for Python 3.11 and 3.12. Python 3.11 is the safer choice as it has the widest compatibility window across all dependencies.
- Avoid Python 3.13 at this time — some dbt dependencies have not yet fully validated 3.13 compatibility as of 2026-05.
- Python 3.10 is acceptable as a minimum but is approaching end-of-life. 3.11 is the recommended target.

### Virtual Environment Location

```
workspace/2026-05-01-itbi-sp-dashboard/.venv/
```

The venv must be created inside the workspace directory, not at the project root, to keep the workspace self-contained. Add `.venv/` to `.gitignore`.

### requirements.txt

```
# Core database
duckdb>=0.10.3,<1.0.0

# dbt transform
dbt-duckdb>=1.8.0,<2.0.0
# Note: dbt-core is pulled as a transitive dependency of dbt-duckdb. Do not pin dbt-core separately.

# XLSX ingestion (Option A — openpyxl only, no pandas)
openpyxl>=3.1.0,<4.0.0

# Dashboard
streamlit>=1.32.0,<2.0.0
plotly>=5.18.0,<6.0.0

# Optional: add if ingestion script needs pre-write transforms
# polars>=0.20.0,<1.0.0
```

**If the team chooses to keep pandas (fallback option):**
```
# Replace openpyxl-only line with:
pandas>=2.0.0,<3.0.0
openpyxl>=3.1.0,<4.0.0
```

### Venv Creation and Makefile Integration

The Makefile must not assume the venv is activated in the shell. All commands should use explicit venv paths:

```makefile
PYTHON = .venv/bin/python
DBT    = .venv/bin/dbt
ST     = .venv/bin/streamlit

.PHONY: venv ingest transform test serve all

venv:
	python3.11 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

ingest:
	$(PYTHON) scripts/ingest.py

transform:
	$(DBT) run --profiles-dir . && $(DBT) test --profiles-dir .

test:
	$(DBT) test --profiles-dir .

serve:
	$(ST) run app/dashboard.py

all: ingest transform serve
```

This ensures `make ingest` works correctly regardless of the user's active shell environment.

---

## Final Agreed Stack

| Category | Tool | Version Pin | Status |
|---|---|---|---|
| Storage | DuckDB | `>=0.10.3,<1.0.0` | AGREED |
| Transform | dbt-duckdb (pulls dbt-core) | `>=1.8.0,<2.0.0` | AGREED |
| Orchestration | Makefile + shell script | N/A | AGREED |
| BI / Viz | Streamlit + Plotly | `streamlit>=1.32, plotly>=5.18` | AGREED |
| Data Quality | dbt tests (built-in) | Included in dbt-core | AGREED |
| Ingestion | Python + openpyxl | `>=3.1.0,<4.0.0` | MODIFIED (pandas removed from ingestion; see Section 6) |
| Python runtime | Python 3.11.x | 3.11.x recommended | ADDED |
| Virtual env | .venv (venv module) | N/A | CONFIRMED |

---

## Explicit Disagreements for Coordinator

None that require mediation. The ingestion library modification (Section 6 / OQ-8) is a preference-level recommendation, not a hard disagreement. If the team prefers `pandas` for ingestion familiarity, it is approved and the pipeline is feasible either way. The Coordinator does not need to mediate — the team can resolve at build time.

---

## Pre-Build Blockers (Must Resolve Before Engineer Writes Code)

| # | Blocker | Owner | Resolution |
|---|---|---|---|
| B1 | Privacy field exclusion list (OQ-2) | Human / Architect | Extract LEGENDA sheet, confirm column names to exclude |
| B2 | Column schema consistency across sheets (OQ-1) | Engineer at build time | Run schema validation script against actual file before ingestion script is finalized |
| B3 | Unique identifier strategy (OQ-3) | Engineer at build time | Run `SELECT COUNT(*) vs SELECT COUNT(DISTINCT guia_number)` after first load |

Items B2 and B3 can be resolved during the first iteration of the build phase by the Engineer. Item B1 requires human input before the ingestion script can be finalized.

---

## Sign-off

Stack validation complete. The Architect's proposal is sound. The agreed stack is feasible on macOS, fully open-source, and appropriate for the project's volume, trigger model, and team skills. The Engineer is ready to proceed to Pipeline Build Mode once B1 (privacy field list) is resolved.
