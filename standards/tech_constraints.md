# Tech Constraints

## Policy: Open-Source Only

All tools recommended or used by any agent must be open-source and self-hostable. Proprietary SaaS tools are prohibited without explicit human approval.

### Prohibited Tools (non-exhaustive)
- Storage / Warehouse: Snowflake, BigQuery, Redshift, Databricks, Azure Synapse
- BI / Viz: Power BI, Tableau, Looker, Qlik
- Transform: dbt Cloud paid features (use open-source dbt core only)
- Orchestration: Managed Airflow (MWAA, Cloud Composer), Dagster Cloud, Prefect Cloud

The approved list below is the authoritative whitelist. Any tool absent from it is implicitly unapproved, regardless of whether it appears in the prohibited list above. All tools in the approved list are self-hostable by definition of their inclusion.

### Approved Tool List

The "(open-source)" and "(self-hosted)" qualifiers are binding. The cloud/managed/commercial variant of any listed tool is treated as a separate, unapproved tool.

| Category | Approved Options |
|---|---|
| Transform | dbt core (open-source, self-hosted only), Apache Spark, Polars, Pandas |
| Storage | DuckDB, PostgreSQL, MySQL, MinIO, Apache Iceberg, Delta Lake |
| Orchestration | Apache Airflow (self-hosted only), Dagster (open-source, self-hosted only), Prefect (open-source, self-hosted only), Mage |
| BI / Viz | Streamlit, Apache Superset, Metabase CE (open-source edition only — not Metabase Cloud), Grafana |
| Data Quality | dbt tests, Great Expectations, Soda Core |
| Catalog / Lineage | OpenMetadata, DataHub, Amundsen |

Any tool not on this list requires explicit human approval. If you believe a non-listed tool is the best fit, include it in the stack proposal under a section titled "Proposed Additions Requiring Human Approval" and do not include it in the confirmed stack until the human approves.

---

## Policy: Virtual Environments

A project is Python-based if it includes any of these tools or dependencies: Dagster, Prefect, Airflow, Great Expectations, Soda Core, Polars, Pandas, Streamlit, or any other Python-executed dependency. When in doubt, apply this policy — venv setup never causes harm.

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

Gate B will automatically FAIL if any item above is absent from `build/pipeline_spec.md`.
