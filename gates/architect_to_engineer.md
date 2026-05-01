# Gate: Architect -> Engineer

## Pass Criteria

### Model Design
- [ ] Business grain explicitly defined
- [ ] Primary and foreign keys defined
- [ ] Source-to-target mapping complete
- [ ] SCD strategy documented
- [ ] DQ rules are testable
- [ ] Freshness SLA from intake.md is addressed in the design (as a DQ freshness rule or an architectural constraint in model_spec.md)
- [ ] Open questions resolved or escalated

### Open-Source Compliance (mandatory — auto-FAIL if any item fails)
- [ ] Every tool referenced in `design/data_contract.md` and `design/model_spec.md` either appears on the approved list in `standards/tech_constraints.md` OR is present in `stack/confirmed_stack.md` (presence in confirmed_stack.md implies human approval was obtained during Phase 1). Any tool absent from both is a FAIL.

### Stack Consistency
- [ ] `stack/confirmed_stack.md` exists and is non-empty
- [ ] No tool (including storage, compute, orchestration, and BI tools) referenced in `design/data_contract.md` or `design/model_spec.md` is absent from `stack/confirmed_stack.md`

## Fail Conditions
- Missing grain or keys
- Ambiguous business rules
- Untestable quality constraints
- Freshness SLA from intake not addressed in the design
- Any tool in design artifacts not on the approved open-source list and not in confirmed_stack.md
- Design artifacts reference a tool absent from confirmed_stack.md
