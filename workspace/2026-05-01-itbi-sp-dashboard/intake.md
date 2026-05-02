# Intake Request

## Request ID
2026-05-01-itbi-sp-dashboard

## Requester
Paulo Guilherme Alencar

## Business Objective
Understand real estate price evolution in São Paulo across 2026 — identifying which neighborhoods have seen the greatest value increases — to support investment and market analysis decisions.

## Key Questions
- How have building transaction prices evolved month-over-month in 2026?
- Which neighborhoods (bairros) have seen the highest price appreciation?
- What is the price per m² trend by area and property type?

## Scope
### In-Scope
- ITBI transaction data for JAN-MAR 2026 (expanding as new months are added)
- Neighborhood-level price evolution and ranking
- Price per m² analysis by area and property use/standard type
- Month-over-month comparison charts
- Auto-detection of new monthly sheets when file is dropped (no code change required)

### Out-of-Scope
- Data before 2026
- Tax calculation or fiscal compliance analysis
- Individual property lookup or search
- Fields marked as personal/fiscal secrecy in LEGENDA sheet

## Time Window
- Analysis period: January 2026 – present (grows monthly)
- Historical range needed: JAN-2026 onward (no prior history available)
- Source file: `data/GUIAS DE ITBI PAGAS (2).xlsx` — one sheet per month (JAN-2026, FEV-2026, MAR-2026, …)

## Data Characteristics
- Estimated volume (rows/day): ~500 (14,735 in Jan / 15,365 in Feb / 19,067 in Mar)
- Estimated volume (GB/month): < 5 MB (XLSX source)
- Update frequency: Monthly — new sheet added to existing XLSX file
- Historical range needed: JAN-2026 to present

## SLA Requirements
- Freshness SLA: N/A — pipeline is triggered manually when a new monthly file is dropped
- Availability requirement: N/A (local machine, no uptime requirement)
- Recovery time objective: N/A (re-run pipeline on demand)

## Infrastructure Context
- Existing infrastructure: none
- Budget sensitivity: cost matters a lot (local machine, open-source only)
- Team technology familiarity: Python, SQL, dbt, Streamlit
- Deployment environment: local machine

## Constraints
- Privacy/compliance: ITBI is São Paulo public open data. Fields marked as personal data or protected by fiscal secrecy in LEGENDA sheet must be excluded from all published outputs (address details, cartório registration numbers).
- Open-source required: YES (project policy — see standards/tech_constraints.md)
- Deadline: none (quality over speed)
- Other: pipeline must auto-detect all month-named sheets (pattern: 3-letter month + hyphen + 4-digit year, e.g. JAN-2026) from the source XLSX — adding a new month must require zero code changes.

## Success Criteria
- Dashboard shows month-over-month transaction price evolution for 2026 with at least 3 chart types
- Neighborhood ranking by value appreciation is visible and filterable by property type
- Price per m² trend is available by neighborhood and month
- Dropping a new monthly sheet into the XLSX and re-running the pipeline updates the dashboard without any code changes

## Stakeholders
- Paulo Guilherme Alencar (requester and end user)

## Tech Stack
- Confirmed stack: DuckDB + dbt core (dbt-duckdb) + Streamlit + Soda Core + openpyxl
- Storage: DuckDB
- Transform: dbt core + dbt-duckdb (Silver layer includes explicit standardization sub-step)
- Orchestration: Makefile (no daemon)
- BI / Viz: Streamlit
- Data Quality: Soda Core (Bronze) + dbt tests (Silver/Gold)
- Ingestion: Python + openpyxl
- Full spec: workspace/2026-05-01-itbi-sp-dashboard/stack/confirmed_stack.md
