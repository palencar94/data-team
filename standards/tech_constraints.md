# Tech Constraints

## Policy: Open-Source Only

All tools recommended or used by any agent must be open-source and self-hostable. Proprietary SaaS tools are prohibited without explicit human approval.

### Prohibited Tools (non-exhaustive)
- Storage / Warehouse: Snowflake, BigQuery, Redshift, Databricks, Azure Synapse
- BI / Viz: Power BI, Tableau, Looker, Qlik
- Transform: dbt Cloud paid features (use open-source dbt core only)
- Orchestration: Managed Airflow (MWAA, Cloud Composer) when a self-hosted alternative exists

### Approved Tool List

| Category | Approved Options |
|---|---|
| Transform | dbt (open-source core), Apache Spark, Polars, Pandas |
| Storage | DuckDB, PostgreSQL, MySQL, MinIO, Apache Iceberg, Delta Lake |
| Orchestration | Apache Airflow (self-hosted), Dagster (open-source), Prefect (open-source), Mage |
| BI / Viz | Streamlit, Apache Superset, Metabase (open-source edition), Grafana |
| Data Quality | dbt tests, Great Expectations, Soda Core |
| Catalog / Lineage | OpenMetadata, DataHub, Amundsen |

Any tool not on this list requires explicit human approval before inclusion in a stack proposal. The Architect must document the approval in the stack proposal file.

---

## Policy: Virtual Environments

Every Python-based project must use an isolated virtual environment. No dependency may be installed globally.

### Setup Requirements

```bash
# Create venv (choose one)
python -m venv .venv
# or: uv venv

# Activate (Linux / macOS)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
# or: pip install -e .
```

### Mandatory Outputs for Every Engineer Build

Every `build/pipeline_spec.md` must include:
- [ ] Virtual environment creation and activation steps
- [ ] Full contents of `requirements.txt` or `pyproject.toml`
- [ ] Note confirming all dependencies are installed inside the venv

Gate B will automatically FAIL if either item above is absent from `build/pipeline_spec.md`.
