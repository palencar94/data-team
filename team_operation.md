# TEAM OPERATING MODEL
## 1) Purpose
This document defines how the AI Data Team operates end-to-end, including ownership, handoffs, required artifacts, quality gates, escalation rules, and definition of done.
---
## 2) Team Workflow (Baseline)
Intake -> Coordinator  
Design -> Architect  
Build/Test -> Engineer  
Analytics/Dashboard -> BI  
Sign-off -> Coordinator
---
## 3) Role Scope
### Coordinator
**Owns**
- Intake triage and scope clarification
- Acceptance criteria definition with stakeholders
- Task decomposition and sequencing across roles
- Gate validation and final release decision
- Risk tracking and escalation handling
**Does not own**
- Detailed model design decisions (Architect)
- Pipeline implementation details (Engineer)
- KPI formula authoring and dashboard semantics (BI)
### Architect
**Owns**
- Data contract design
- Medallion model design (bronze/silver/gold)
- Grain, keys, joins, SCD strategy
- Data quality rules at design level
- Naming/governance compliance in design artifacts
**Does not own**
- Production pipeline implementation
- Dashboard creation
- KPI business definitions outside approved glossary
### Engineer
**Owns**
- Ingestion and transformation implementation
- Build and operation of bronze/silver/gold pipelines
- Test implementation and execution evidence
- Reliability, observability, and runbook notes
- Handoff package for BI consumption
**Does not own**
- Redefining approved model semantics
- KPI business meaning changes
- Final stakeholder sign-off decision
### BI
**Owns**
- KPI implementation from approved glossary
- Semantic consistency of metrics
- Dashboard layout, filters, and drilldowns
- Reconciliation and validation evidence
- Stakeholder-facing insight narrative
**Does not own**
- Production use of raw/bronze data for published KPIs
- Inventing KPI formulas not in glossary
- Changing model logic without Architect/Engineer alignment
---
## 4) Handoff Sequence and RACI
1. **Intake (Coordinator)**
   - Receives request, clarifies scope, defines acceptance criteria.
2. **Design (Architect)**
   - Produces architecture artifacts and design constraints.
3. **Build/Test (Engineer)**
   - Implements and validates pipelines and data outputs.
4. **Analytics/Dashboard (BI)**
   - Builds KPI layer and dashboard outputs with validation.
5. **Sign-off (Coordinator)**
   - Runs final gate checks and issues READY/NOT READY.
---
## 5) Required Artifacts Per Stage
### Intake -> Coordinator
- Completed intake request
- Scoped problem statement
- In-scope / out-of-scope list
- Acceptance criteria
- Initial risk log
### Design -> Architect
- Data contract
- Model specification (grain, keys, SCD, mappings)
- DQ rule set
- Open questions / assumptions list
### Build/Test -> Engineer
- Pipeline specification
- Transformation summary by layer
- Test plan and evidence
- Operational runbook notes
- BI handoff note (gold datasets + caveats)
### Analytics/Dashboard -> BI
- Dashboard specification
- KPI definition mapping to glossary
- Reconciliation evidence
- Filter/drilldown validation notes
- Insight narrative and caveats
### Sign-off -> Coordinator
- Gate checklist results
- Final acceptance summary
- Open issues and owners
- READY / NOT READY decision
---
## 6) Quality Gates Per Stage
### Gate A: Architect -> Engineer
**Pass criteria**
- Grain explicitly defined
- Primary/foreign keys defined
- Source-to-target mapping complete
- SCD strategy documented
- DQ rules testable
**Fail conditions**
- Ambiguous grain or keys
- Incomplete mappings
- Untestable or missing DQ rules
### Gate B: Engineer -> BI
**Pass criteria**
- Gold datasets available and documented
- Mandatory tests pass (or approved exceptions)
- Freshness checks meet policy (or approved exceptions)
- Known caveats explicitly documented
**Fail conditions**
- Critical tests failing
- Missing gold documentation
- Undocumented caveats
### Gate C: BI -> Coordinator
**Pass criteria**
- KPI formulas match glossary
- Reconciliation evidence provided
- Filters and drilldowns validated
- Edge cases tested and documented
**Fail conditions**
- KPI mismatch with glossary
- Missing validation evidence
- Unverified dashboard behavior
---
## 7) Escalation Rules
Escalate to Coordinator immediately when:
- Inputs are ambiguous or contradictory
- A required artifact is missing at handoff
- A quality gate fails twice
- KPI definitions conflict with glossary
- SLA/freshness targets are at risk
- Scope changes materially during execution
Coordinator escalation actions:
- Stop downstream handoff
- Clarify decision owner and deadline
- Record decision and update scope/artifacts
- Re-run affected gate before continuing
---
## 8) Definition of Done (DoD)
A request is **Done** only when all conditions are met:
- All required stage artifacts are completed
- All quality gates pass (or approved exceptions documented)
- Acceptance criteria are fully satisfied
- KPI definitions align with glossary
- Known caveats/risks are documented with owners
- Coordinator issues final **READY** decision
If any condition is unmet, status is **NOT READY**.
---
## 9) Operating Principles
- Single owner per stage; no overlapping accountability
- No handoff without required artifacts
- No stage bypasses quality gates
- No KPI publication without glossary alignment
- Document decisions and exceptions explicitly