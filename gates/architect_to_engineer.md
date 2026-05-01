# Gate: Architect -> Engineer

## Pass Criteria

### Model Design
- [ ] Business grain explicitly defined
- [ ] Primary and foreign keys defined
- [ ] Source-to-target mapping complete
- [ ] SCD strategy documented
- [ ] DQ rules are testable
- [ ] Open questions resolved or escalated

### Open-Source Compliance (mandatory — auto-FAIL if any item fails)
- [ ] Every tool referenced in design artifacts is on the approved list in `standards/tech_constraints.md`
- [ ] No proprietary SaaS tool is referenced anywhere in `design/data_contract.md` or `design/model_spec.md`
- [ ] If any non-listed tool is used, explicit human approval is documented in `stack/stack_proposal.md`

### Stack Consistency
- [ ] `stack/confirmed_stack.md` exists and is non-empty
- [ ] All storage and compute tools referenced in model spec match the confirmed stack
- [ ] No tool appears in design artifacts that is not in the confirmed stack

## Fail Conditions
- Missing grain or keys
- Ambiguous business rules
- Untestable quality constraints
- Any tool not on the approved open-source list (unless approved)
- Design artifacts inconsistent with confirmed stack
