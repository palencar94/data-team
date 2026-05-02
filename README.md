# Data Team — Autonomous AI Data Engineering Framework

An autonomous AI data team with 4 specialist roles that orchestrates the full lifecycle of a data project: from intake and stack selection through data modeling, pipeline engineering, and BI delivery.

---

## Overview

This framework simulates a real data team using AI agents, each with a distinct role and scope. A **Coordinator** agent manages the full workflow, dispatching specialized subagents at each phase and enforcing quality gates at every handoff.

```
User request
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                      Coordinator                        │
│   Intake → Stack Selection → Gate A → Gate B → Gate C  │
└────┬──────────────┬──────────────┬──────────────────────┘
     │              │              │
     ▼              ▼              ▼
 Architect      Engineer        BI Specialist
 (design)       (build)         (analytics)
```

### The 4 Roles

| Role | Agent | Responsibility |
|------|-------|----------------|
| **Coordinator** | `agents/coordinator.md` | Orchestrates phases, evaluates gates, makes final delivery decision |
| **Data Architect** | `agents/data_architect.md` | Proposes stack, designs medallion data model and contracts |
| **Data Engineer** | `agents/data_engineer.md` | Implements pipeline, test plan, and BI handoff |
| **BI Specialist** | `agents/data_bi.md` | Builds dashboard spec and validates KPI alignment |

---

## The 6-Phase Workflow

| Phase | Owner | Output |
|-------|-------|--------|
| 0 — Intake | Coordinator | `workspace/<id>/intake.md` |
| 1 — Stack Selection | Architect + Engineer | `stack_proposal.md`, `stack_validation.md`, `confirmed_stack.md` |
| 2 — Design | Architect | `data_contract.md`, `model_spec.md` → **Gate A** |
| 3 — Build | Engineer | `pipeline_spec.md`, `test_plan.md`, `bi_handoff.md` → **Gate B** |
| 4 — Analytics | BI Specialist | `dashboard_spec.md`, `validation_notes.md` → **Gate C** |
| 5 — Sign-off | Coordinator | `release_checklist.md` + final READY/NOT READY decision |

Human confirmation is required after Intake and after Stack Selection before any code or design work begins.

---

## Quality Gates

Each gate evaluates the preceding phase output against a structured checklist:

- **Gate A** (`gates/architect_to_engineer.md`) — Design completeness and adherence to standards
- **Gate B** (`gates/engineer_to_bi.md`) — Pipeline correctness, test coverage, BI readiness
- **Gate C** (`gates/bi_to_coordinator.md`) — KPI accuracy, chart coverage, dashboard completeness

On gate failure: the Coordinator retries (up to 2x), re-scopes, or escalates to the human.

---

## Stack Policy

All tools must be **open-source and self-hostable**. The approved list includes:

| Category | Options |
|----------|---------|
| Transform | dbt core, Apache Spark, Polars, Pandas |
| Storage | DuckDB, PostgreSQL, MySQL, MinIO, Apache Iceberg |
| Orchestration | Airflow, Dagster, Prefect, Mage |
| BI / Viz | Streamlit, Apache Superset, Metabase CE, Grafana |
| Data Quality | dbt tests, Great Expectations, Soda Core |

Proprietary SaaS tools (Snowflake, BigQuery, Tableau, Power BI, etc.) are prohibited. See [`standards/tech_constraints.md`](standards/tech_constraints.md) for the full policy.

---

## Slash Command

When using Claude Code, trigger a new data request with:

```
/data-request <description of what you need>
```

The Coordinator will ask clarifying questions one at a time, produce a filled intake document, and wait for your confirmation before doing any work.

---

## Project Structure

```
data-team/
├── agents/               # Role prompts for each team member
│   ├── coordinator.md
│   ├── data_architect.md
│   ├── data_engineer.md
│   └── data_bi.md
├── standards/            # Shared policies enforced across all agents
│   ├── tech_constraints.md     # Open-source-only stack policy
│   ├── naming_conventions.md
│   ├── layer_definitions.md    # Bronze / Silver / Gold definitions
│   ├── kpi_glossary.md
│   ├── sla_freshness_policy.md
│   └── testing_policy.md
├── gates/                # Quality gate checklists for each handoff
│   ├── architect_to_engineer.md
│   ├── engineer_to_bi.md
│   └── bi_to_coordinator.md
├── templates/            # Artifact templates used by agents
│   ├── intake.md
│   ├── data_contract.md
│   ├── model_spec.md
│   ├── dashboard_spec.md
│   ├── test_plan.md
│   └── release_checklist.md
├── knowledge/            # Project-specific knowledge for active projects
│   └── itbi_sp/          # São Paulo ITBI dashboard (see below)
├── workspace/            # Active request workspaces (one folder per request)
└── docs/                 # Design specs and implementation plans
```

---

## Example Project: ITBI SP Dashboard

The first project built by this team is a **São Paulo real estate market dashboard** powered by public ITBI (property transfer tax) data.

### What It Does

- Ingests monthly XLSX sheets from the Prefeitura de São Paulo
- Runs a Bronze → Silver → Gold medallion pipeline with dbt + DuckDB
- Enriches ~41% of transactions with neighborhood data via CEP lookup
- Delivers a Streamlit dashboard with 3 analysis sections

### Stack

| Layer | Tool |
|-------|------|
| Storage | DuckDB |
| Transform | dbt core + dbt-utils |
| Data Quality | Soda Core |
| Dashboard | Streamlit + Plotly |
| Language | Python 3.9 |

### Dashboard Sections

| Section | Description |
|---------|-------------|
| A — City-Wide Trends | MoM median price evolution (line + bar), price/m² trend (area chart), KPI summary cards |
| B — Neighborhood Ranking | Top-N neighborhoods by price (horizontal bar), sortable stats table |
| C — Price per m² Drill-down | Multi-series line by use type, grouped bar comparison across neighborhoods |

### Quick Start

```bash
# Prerequisites: Python 3.9, .env with DB_PATH set

make venv
source .venv/bin/activate
make install
make dbt-deps
make pipeline   # ingest → load-cep → soda-bronze → dbt-seed → dbt-run → dbt-test
make serve      # launches http://localhost:8501
```

Adding a new monthly sheet: drop the sheet named `MMM-YYYY` into the XLSX and run `make pipeline`. No code changes required.

### Key Facts

- **49,164 transactions** across JAN–MAR 2026
- **4,524 neighborhoods** after CEP enrichment (was 41% NULL bairro in source)
- **46 dbt tests** — 39 PASS, 7 intentional WARN (documented in [`knowledge/itbi_sp/06_known_data_quality.md`](knowledge/itbi_sp/06_known_data_quality.md))
- Full project knowledge base: [`knowledge/itbi_sp/`](knowledge/itbi_sp/)

---

## Standards Reference

| Standard | File |
|----------|------|
| Stack / tool policy | [`standards/tech_constraints.md`](standards/tech_constraints.md) |
| Naming conventions | [`standards/naming_conventions.md`](standards/naming_conventions.md) |
| Layer definitions (Bronze/Silver/Gold) | [`standards/layer_definitions.md`](standards/layer_definitions.md) |
| KPI glossary | [`standards/kpi_glossary.md`](standards/kpi_glossary.md) |
| SLA & freshness | [`standards/sla_freshness_policy.md`](standards/sla_freshness_policy.md) |
| Testing policy | [`standards/testing_policy.md`](standards/testing_policy.md) |
