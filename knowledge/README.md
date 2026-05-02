# Project Knowledge Base

This directory contains project-specific knowledge documents. Each sub-directory maps to one active project by its request-id.

## How Agents Use This

When the Coordinator dispatches a subagent on a request related to an existing project, it injects the relevant knowledge documents into the dispatch context alongside the workspace artifacts.

**Every agent must read the knowledge files that match their role before beginning work. Knowledge documents describe decisions already made, schemas already deployed, and pitfalls already encountered — re-deriving them wastes time and risks contradictions.**

## Structure

```
knowledge/
  README.md                  ← this file
  itbi_sp/                   ← project: ITBI SP Dashboard (request-id: 2026-05-01-itbi-sp-dashboard)
    01_project_overview.md
    02_data_sources.md
    03_medallion_architecture.md
    04_schema_reference.md
    05_pipeline_runbook.md
    06_known_data_quality.md
    07_tech_decisions.md
    08_dashboard_reference.md
```

## Reading Order by Role

| Role | Files to read |
|------|--------------|
| Coordinator | 01, 03 |
| Data Architect | 01, 02, 03, 04, 07 |
| Data Engineer | 02, 03, 04, 05, 06, 07 |
| BI Specialist | 01, 03, 04, 06, 08 |

## Maintenance

Update knowledge documents whenever:
- A new table or column is added/removed
- A data quality issue is resolved or discovered
- An architectural decision changes
- A new data source is onboarded
- A known pipeline failure mode is documented

Knowledge documents are **living documents**. They do not track history — for history, see git log or the coordinator decision log.
