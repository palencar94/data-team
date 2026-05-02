# Release Checklist
## Request: 2026-05-01-itbi-sp-dashboard
## Date: 2026-05-01

## Artifacts
- [x] Intake completed — `workspace/2026-05-01-itbi-sp-dashboard/intake.md`
- [x] Data contract approved — `workspace/2026-05-01-itbi-sp-dashboard/design/data_contract.md`
- [x] Model spec approved — `workspace/2026-05-01-itbi-sp-dashboard/design/model_spec.md`
- [x] Pipeline spec completed — `workspace/2026-05-01-itbi-sp-dashboard/build/pipeline_spec.md`
- [x] Test plan evidence attached — `workspace/2026-05-01-itbi-sp-dashboard/build/test_plan.md`
- [x] Dashboard spec completed — `workspace/2026-05-01-itbi-sp-dashboard/analytics/dashboard_spec.md`
- [x] Validation notes completed — `workspace/2026-05-01-itbi-sp-dashboard/analytics/validation_notes.md`
- [x] BI handoff completed — `workspace/2026-05-01-itbi-sp-dashboard/build/bi_handoff.md`

## Gates
- [x] Architect → Engineer: PASS — `gates/gate_a_result.md`
- [x] Engineer → BI: PASS — `gates/gate_b_result.md`
- [x] BI → Coordinator: PASS — `gates/gate_c_result.md`

## Quality
- [x] KPI glossary alignment verified — 5 KPIs registered with full glossary fields
- [x] Freshness/SLA verified — Tier 2 (manual trigger); Soda Core 35-day freshness check defined
- [x] Known caveats documented — 8 caveats in bi_handoff.md; all surfaced in dashboard_spec.md
- [x] Open-source compliance — all tools on approved list in standards/tech_constraints.md
- [x] Virtual environment documented — requirements.txt + venv setup in pipeline_spec.md Section 7

## Readiness
- [x] Stakeholder review: pending (Paulo Guilherme Alencar — owner and end user)
- [x] Rollback/mitigation: full pipeline is re-runnable; all models are full-refresh; no incremental state to roll back; drop new XLSX = re-ingest
- [x] Final coordinator decision: **READY**

## Acceptance Criteria Check

| Criterion | Status |
|---|---|
| Dashboard shows MoM transaction price evolution with ≥ 3 chart types | READY — 3 Plotly charts specified (line, bar, multi-series line) |
| Neighborhood ranking filterable by property type | READY — uso_desc multiselect filter in Chart 3 |
| Price per m² trend by neighborhood and month | READY — gold_itbi_price_per_m2 drives Chart 3 |
| New monthly sheet → re-run → dashboard updates with zero code changes | READY — sheet auto-detection via regex; all models full-refresh |
