# Gate: BI -> Coordinator

## Pass Criteria

### Analytics Outputs
- [ ] All KPIs map to definitions in `standards/kpi_glossary.md`
- [ ] Reconciliation check results and evidence documented in `analytics/validation_notes.md`
- [ ] Filter/drilldown test evidence included (screenshots, data comparisons, or written results)
- [ ] Edge-case behavior documented
- [ ] Stakeholder narrative included in `analytics/dashboard_spec.md`

### Stack Compliance
- [ ] `stack/confirmed_stack.md` exists and is non-empty (pre-condition — if absent, escalate immediately)
- [ ] No tool referenced in `analytics/dashboard_spec.md` or `analytics/validation_notes.md` is absent from `stack/confirmed_stack.md`

## Fail Conditions
- KPI formula does not match glossary definition
- Missing reconciliation evidence (description alone is not evidence)
- Filter/drilldown test evidence absent
- Missing stakeholder narrative
- Dashboard artifacts reference a tool not in confirmed_stack.md
- A proprietary tool appears in any analytics artifact
