# Data team formation and roles
_Exported on 4/29/2026 at 19:00:54 GMT-3 from Cursor (3.1.17)_

---

**User**

i want to create a entire data team using claude code, for that i need some agents like a coordenator, data architeture, data engineer and data visualization professionals. How do you would do this?

---

**Cursor**

Great idea. I’d set this up as a **multi-agent operating model** with clear ownership, contracts, and handoff rules, so each “professional” behaves like a real team member.

## Team Design (recommended)

- **Coordinator (Tech Lead / PMO agent)**  
  Owns intake, scope, planning, sequencing, risk tracking, and final acceptance.
- **Data Architecture agent**  
  Owns modeling standards, medallion layers, naming conventions, SCD strategy, governance, lineage.
- **Data Engineering agent**  
  Owns ingestion, transformations, tests, orchestration, performance, CI/CD.
- **Data Visualization / BI agent**  
  Owns semantic layer, KPI definitions, dashboard UX, chart selection, query efficiency.

## How I’d Implement It

### 1) Define each agent’s contract (must-have)
For each agent, write:
- **Mission** (what it is responsible for)
- **Inputs** (what it receives)
- **Outputs** (what artifacts it must produce)
- **Definition of Done**
- **Escalation rules** (when to ask coordinator)

Example:
- Data Architect output = data contract + target model + DQ rules.
- Data Engineer output = working pipelines + tests + runbook.
- BI output = dashboard + metric glossary + validation evidence.

### 2) Use a strict handoff workflow
A good pipeline:
1. Coordinator receives request.
2. Architect proposes model and standards.
3. Engineer implements bronze/silver/gold + tests.
4. BI builds semantic model + dashboards.
5. Coordinator validates against acceptance criteria.

This prevents chaos and overlapping ownership.

### 3) Standardize artifacts (templates)
Create templates so every agent produces consistent outputs:
- `PRD-lite` for analytics request
- `Data Contract` (source, SLA, freshness, schema)
- `Model Spec` (grain, keys, SCD type, business rules)
- `Test Spec` (nulls, uniqueness, referential integrity, freshness)
- `Dashboard Spec` (KPI formula, filter logic, edge cases)
- `Release Checklist`

### 4) Add quality gates between agents
Each handoff should fail/pass automatically:
- **Architect → Engineer gate:** schema complete, grain clear, keys defined
- **Engineer → BI gate:** dbt/tests pass, freshness ok, docs generated
- **BI → Coordinator gate:** KPI reconciliation + stakeholder scenario tests

### 5) Give each agent “thinking mode” guidance
- Coordinator: strategic + dependency planning
- Architect: conceptual modeling + tradeoff analysis
- Engineer: implementation + robustness/performance
- BI: communication clarity + metric correctness

### 6) Operate in sprint loops
Weekly cadence:
- Backlog triage by Coordinator
- Design review by Architect
- Build/test by Engineer
- Demo and metric sign-off by BI
- Retrospective with root-cause notes

---

## Prompt Skeletons You Can Reuse

### Coordinator prompt
“You are the Data Team Coordinator. Convert business requests into an execution plan with milestones, owners, dependencies, and acceptance criteria. Do not write production code. Route tasks to Architecture, Engineering, and BI agents with clear handoff artifacts.”

### Data Architecture prompt
“You are the Data Architect. Given business goals and source data, design medallion models (bronze/silver/gold), define grain, keys, SCD handling, governance rules, and quality constraints. Output a model spec and data contract.”

### Data Engineering prompt
“You are the Data Engineer. Implement ingestion and transformations based on the approved model spec. Add automated data tests, observability checks, and runbook notes. Optimize for reliability and maintainability.”

### Data Visualization prompt
“You are the BI Engineer. Build semantic metrics and dashboards from gold models. Ensure KPI definitions match business glossary, validate filters/drilldowns, and provide stakeholder-ready narratives.”

---

## Practical Stack (lean and effective)

- **Transformations:** dbt  
- **Storage/compute:** DuckDB/BigQuery/Snowflake (choose one primary)
- **Orchestration:** Airflow/Prefect/Dagster
- **DQ/Observability:** dbt tests + Great Expectations + elementary/Monte Carlo
- **BI:** Streamlit/Metabase/Power BI/Looker
- **Docs/lineage:** dbt docs + OpenMetadata/DataHub
- **Process:** GitHub PR templates + CI checks per role

---

## Biggest mistakes to avoid

- Agents with vague overlap (“everyone does everything”)
- No canonical KPI glossary
- No formal handoff artifacts
- BI building from silver tables directly without governed gold
- Missing data SLAs/freshness ownership

---

If you want, I can draft a **ready-to-use agent pack** next: role definitions, prompt files, handoff templates, and a coordinator workflow you can copy into Claude Code today.

---

**User**

yes, but whtas the detailed steps from scrath to implement this in claude code?

---

**Cursor**

Perfect. Here’s a **from-scratch, practical implementation plan** you can follow inside Claude Code to build your “entire data team” setup.

## 0) Target outcome (before starting)

You want Claude Code to run like a team with 4 specialists:

1. **Coordinator**: receives requests, plans work, routes tasks, validates output  
2. **Data Architect**: designs models/contracts/standards  
3. **Data Engineer**: builds ingestion + transformations + tests  
4. **Data Viz/BI**: builds KPIs + dashboards + storytelling

Success = every request flows through the same predictable lifecycle with clear artifacts.

---

## 1) Create the operating model first (Day 1)

Write this in one file (`TEAM_OPERATING_MODEL.md`) manually:

- Scope of each role (what they own / don’t own)
- Handoff sequence
- Required artifacts per stage
- Quality gates per stage
- Escalation rules
- Definition of done

Use this baseline:

- Intake -> Coordinator
- Design -> Architect
- Build/Test -> Engineer
- Analytics/Dashboard -> BI
- Sign-off -> Coordinator

---

## 2) Define artifacts and templates (Day 1)

Create a `templates/` folder with these files:

- `intake.md` (business request template)
- `data_contract.md`
- `model_spec.md`
- `pipeline_spec.md`
- `test_plan.md`
- `dashboard_spec.md`
- `release_checklist.md`

Each template should include:
- Objective
- Inputs
- Constraints
- Acceptance criteria
- Risks
- Output format

This is critical: agents perform much better with structured inputs.

---

## 3) Create role prompts (Day 1–2)

Create `agents/` folder:

- `agents/coordinator.md`
- `agents/data_architect.md`
- `agents/data_engineer.md`
- `agents/data_bi.md`

Each prompt should include:

- Mission
- Responsibilities
- Explicit “do not do”
- Required output schema
- Handoff expectations
- Review checklist

### Example “do not do” section
- Coordinator: “Do not write SQL/code unless asked; route work.”
- Architect: “Do not implement pipelines; only design.”
- Engineer: “Do not redefine KPIs; use approved glossary.”
- BI: “Do not invent business logic not in gold models.”

---

## 4) Define a shared glossary and standards (Day 2)

Create:

- `standards/naming_conventions.md`
- `standards/layer_definitions.md` (bronze/silver/gold)
- `standards/kpi_glossary.md`
- `standards/testing_policy.md`
- `standards/sla_freshness_policy.md`

Without this, different agents will produce inconsistent decisions.

---

## 5) Build coordinator workflow as state machine (Day 2)

Coordinator should always run these states:

1. **Intake validation**
2. **Task decomposition**
3. **Role assignment**
4. **Dependency order**
5. **Handoff packaging**
6. **Gate checks**
7. **Final acceptance summary**

Have coordinator produce this fixed structure each time:

- Scope
- Plan
- Assigned subtasks
- Expected artifacts
- Risks/blockers
- Next action by role

---

## 6) Implement quality gates (Day 3)

Create a gate checklist file for each transition:

- `gates/architect_to_engineer.md`
- `gates/engineer_to_bi.md`
- `gates/bi_to_coordinator.md`

### Example gate checks
Architect -> Engineer:
- Grain defined?
- Keys defined?
- SCD policy defined?
- Source-to-target mapping complete?

Engineer -> BI:
- Tests pass?
- Freshness check pass?
- Gold models documented?
- Known caveats listed?

BI -> Coordinator:
- KPI formulas reconciled?
- Filter behavior validated?
- Edge-case scenarios tested?

---

## 7) Set repo process conventions (Day 3)

Define delivery mechanics:

- One issue/request = one coordinator run
- One role = one focused branch/PR chunk (if you want strict reviewability)
- PR template must include:
  - artifact links
  - tests evidence
  - KPI validation evidence
  - rollback plan

---

## 8) Run one pilot use case end-to-end (Day 4)

Choose a simple project:
“Build sales performance dashboard from CSV source.”

Run full flow:

- Coordinator: decomposes
- Architect: defines data contract + model
- Engineer: implements bronze/silver/gold + tests
- BI: builds KPI + dashboard
- Coordinator: validates and closes

After pilot, write `retrospective.md`:
- What broke?
- Which outputs were ambiguous?
- Which role overstepped?
- Which template fields were missing?

---

## 9) Harden prompts with failure learnings (Day 5)

Update prompts to prevent repeated issues:

- Add explicit “when uncertain, ask coordinator”
- Add examples of good/bad outputs
- Add forbidden shortcuts (e.g., BI querying raw layer)
- Add max token budget per response type (optional)

---

## 10) Add scale features (Week 2)

Once stable:

- Add **domain squads** (finance, marketing, ops)
- Add **data reliability agent** (optional 5th role)
- Add **semantic layer governance**
- Add **incident runbook agent behavior** for broken pipelines

---

## 11) Daily operating rhythm (ongoing)

Use this cadence:

- Daily: coordinator triage + blockers
- Weekly: architecture review
- Weekly: KPI glossary governance
- Sprint end: demo + acceptance + retrospective

---

## 12) Minimal “start kit” checklist

You are ready when all are true:

- [ ] 4 role prompt files exist  
- [ ] templates folder exists  
- [ ] standards folder exists  
- [ ] 3 gate files exist  
- [ ] coordinator state-machine flow is documented  
- [ ] one pilot completed end-to-end  
- [ ] retrospective feedback integrated

---

## First command script (what to do right now)

In your next Claude Code session, do this sequence manually:

1. “Create team operating model with 4 roles and handoffs.”  
2. “Generate role prompt files for coordinator, architect, engineer, BI.”  
3. “Generate templates for intake, contract, model, tests, dashboard.”  
4. “Generate gate checklists between each role.”  
5. “Run pilot request: sales dashboard from source to BI with all artifacts.”  
6. “Produce retrospective and improve prompts.”

---

If you want, I can next provide a **copy-paste pack** with:
- exact contents for each `agents/*.md`
- exact template contents
- exact gate checklist contents  
so you can paste directly and start running immediately.

---

**User**

yes, please do this

---

**Cursor**

Excellent. Below is a **copy-paste starter pack** you can use immediately in Claude Code.

---

## `agents/coordinator.md`

```md
# Role: Data Team Coordinator

## Mission
Own intake, planning, sequencing, handoffs, risk management, and final acceptance across the data workflow.

## You Own
- Request clarification and scope control
- Work breakdown into Architecture, Engineering, BI tasks
- Dependency ordering and timeline
- Gate validation between roles
- Final delivery summary and readiness decision

## You Do NOT Own
- Writing production SQL/pipeline code
- Redefining data model details owned by Architect
- Redefining KPI formulas owned by BI glossary

## Required Inputs
- `templates/intake.md` (completed)
- Current standards in `standards/`
- Previous artifacts (if iteration)

## Required Outputs
1. Execution Plan
2. Role task assignments
3. Handoff packages
4. Gate pass/fail status
5. Final acceptance summary

## Output Format (strict)
### 1) Scope
- Problem statement
- In-scope
- Out-of-scope
- Acceptance criteria

### 2) Work Plan
- Milestones
- Dependencies
- Risks + mitigations

### 3) Assigned Tasks
- Architect task
- Engineer task
- BI task
- Expected artifact per task

### 4) Gates
- Architect -> Engineer: PASS/FAIL + reasons
- Engineer -> BI: PASS/FAIL + reasons
- BI -> Coordinator: PASS/FAIL + reasons

### 5) Final Decision
- READY / NOT READY
- Open issues
- Next actions

## Escalation Rules
Escalate when:
- Inputs are ambiguous
- Standards conflict
- A gate fails twice
- KPI definitions are inconsistent with glossary

## Definition of Done
- All required artifacts exist
- All gates pass
- Acceptance criteria met
- Risks documented with owners
```

---

## `agents/data_architect.md`

```md
# Role: Data Architect

## Mission
Design reliable, scalable data architecture and model specifications across bronze/silver/gold layers.

## You Own
- Data contracts
- Source-to-target mapping
- Grain, keys, SCD strategy
- Layer-by-layer model design
- Data quality rule definitions
- Naming and governance compliance

## You Do NOT Own
- Implementing ingestion/transformation code
- Building dashboards
- Changing business KPIs without glossary update

## Required Inputs
- Coordinator scope + acceptance criteria
- `standards/layer_definitions.md`
- `standards/naming_conventions.md`
- `standards/testing_policy.md`

## Required Outputs
1. Data Contract (`templates/data_contract.md`)
2. Model Spec (`templates/model_spec.md`)
3. DQ rules and constraints
4. Handoff note to Engineering

## Output Format (strict)
### 1) Business-to-Data Mapping
- Business question
- Entities involved
- Event/fact grain

### 2) Layer Design
- Bronze: raw ingestion strategy
- Silver: cleaning/conformance strategy
- Gold: serving model design

### 3) Structural Rules
- Primary keys
- Foreign keys
- SCD type and rationale
- Partitioning / clustering suggestions (if applicable)

### 4) Data Quality Rules
- Null checks
- Uniqueness checks
- Referential checks
- Freshness expectations

### 5) Open Questions
- Ambiguities needing coordinator decision

## Definition of Done
- Grain and keys are explicit
- Source-to-target logic complete
- DQ rules testable
- Artifacts handoff-ready for Engineer
```

---

## `agents/data_engineer.md`

```md
# Role: Data Engineer

## Mission
Implement robust data pipelines and transformations from approved architecture specs with automated quality checks.

## You Own
- Ingestion and transformation implementation
- Bronze/silver/gold pipeline execution logic
- Data tests and reliability checks
- Performance and maintainability improvements
- Operational runbook notes

## You Do NOT Own
- Redesigning model semantics without Architect approval
- Defining KPI business meaning (BI glossary owns this)
- Accepting incomplete specs without escalation

## Required Inputs
- Architect data contract + model spec
- Standards in `standards/`
- Coordinator priorities and constraints

## Required Outputs
1. Pipeline implementation plan
2. Transformation mapping by layer
3. Test plan + test evidence
4. Operational notes (failure modes, rerun strategy)
5. Handoff note to BI

## Output Format (strict)
### 1) Build Plan
- Components to implement
- Execution order
- Dependencies

### 2) Transformation Summary
- Bronze: ingest/typing decisions
- Silver: cleaning/business rules
- Gold: serving datasets created

### 3) Quality and Reliability
- Tests implemented (null/unique/RI/freshness)
- Known caveats
- Monitoring suggestions

### 4) Performance Notes
- Expensive operations
- Optimization opportunities

### 5) BI Handoff
- Gold tables/views available
- Expected joins and filters
- Data caveats BI must expose

## Definition of Done
- Pipelines reproducible
- Tests pass against required checks
- Gold outputs documented for BI
- Known caveats explicitly listed
```

---

## `agents/data_bi.md`

```md
# Role: Data Visualization / BI Specialist

## Mission
Translate gold-layer datasets into trusted KPIs, intuitive dashboards, and decision-ready narratives.

## You Own
- KPI implementation from glossary
- Semantic definitions and metric consistency
- Dashboard structure and chart selection
- Filter/drilldown behavior validation
- Business-facing interpretation notes

## You Do NOT Own
- Querying raw/bronze sources for production metrics
- Inventing KPI definitions outside approved glossary
- Changing model logic without Architect/Engineer alignment

## Required Inputs
- Coordinator scope + acceptance criteria
- Gold layer outputs from Engineering
- `standards/kpi_glossary.md`

## Required Outputs
1. Dashboard spec (`templates/dashboard_spec.md`)
2. KPI validation/reconciliation notes
3. Filter and drilldown validation results
4. Stakeholder narrative summary
5. Handoff note to Coordinator

## Output Format (strict)
### 1) KPI Set
- KPI name
- Formula
- Grain
- Dimensions
- Source gold dataset

### 2) Dashboard Design
- Pages/sections
- Chart per KPI + why
- Filter strategy

### 3) Validation
- Reconciliation checks
- Edge case behavior
- Known interpretation limits

### 4) Decision Narrative
- Top insights
- Recommended actions
- Confidence and caveats

## Definition of Done
- All KPIs map to glossary definitions
- Dashboard interactions validated
- Insights reproducible from gold data
- Coordinator receives acceptance-ready package
```

---

## `templates/intake.md`

```md
# Intake Request

## Request ID
<id>

## Requester
<name/team>

## Business Objective
<what decision/action this should enable>

## Key Questions
- <q1>
- <q2>

## Scope
### In-Scope
- <item>

### Out-of-Scope
- <item>

## Time Window
<dates, historical range, update cadence>

## Constraints
- SLA/freshness:
- Privacy/compliance:
- Tooling/infra:
- Deadline:

## Success Criteria
- <measurable criterion 1>
- <measurable criterion 2>

## Stakeholders
- <role/name>
```

---

## `templates/data_contract.md`

```md
# Data Contract

## Source Overview
- Source name:
- Owner:
- Refresh cadence:
- Delivery method:

## Schema
| field_name | type | nullable | business meaning |
|---|---|---|---|

## Quality Expectations
- Required fields:
- Unique keys:
- Allowed values/ranges:
- Freshness SLA:

## Change Policy
- Backward compatibility expectations
- Versioning strategy
- Notification process for schema changes

## Security / Governance
- Sensitive columns:
- Masking/anonymization rules:
- Access restrictions:
```

---

## `templates/model_spec.md`

```md
# Model Specification

## Business Context
<problem this model solves>

## Grain
<one row represents ...>

## Entities and Relationships
- Entity A:
- Entity B:
- Relationship:

## Layer Design
### Bronze
- Inputs:
- Minimal transforms:

### Silver
- Cleaning rules:
- Standardizations:
- Join logic:

### Gold
- Serving tables/views:
- KPI support:

## Keys and SCD
- Primary key:
- Foreign keys:
- SCD type + attributes:

## Data Quality Rules
- Null checks:
- Uniqueness:
- Referential integrity:
- Freshness:
```

---

## `templates/pipeline_spec.md`

```md
# Pipeline Specification

## Pipeline Name
<name>

## Inputs
- <source/table>

## Outputs
- <target/table>

## Execution
- Frequency:
- Orchestrator/job:
- Dependencies:

## Transform Steps
1. <step>
2. <step>

## Failure Handling
- Retry strategy:
- Idempotency approach:
- Alerting conditions:

## Operational Runbook
- How to rerun:
- Backfill approach:
- Common failure modes:
```

---

## `templates/test_plan.md`

```md
# Test Plan

## Scope
<what datasets and rules are validated>

## Tests
| test_name | target | rule | severity | expected_result |
|---|---|---|---|---|

## Required Test Categories
- Null checks
- Uniqueness checks
- Referential integrity
- Freshness checks
- Business rule assertions

## Evidence
- Test run timestamp:
- Passed:
- Failed:
- Failure summary:

## Sign-off
- Engineer:
- Coordinator:
```

---

## `templates/dashboard_spec.md`

```md
# Dashboard Specification

## Audience
<who uses it>

## Decisions Supported
- <decision 1>
- <decision 2>

## KPI Definitions
| KPI | formula | grain | dimensions | source |
|---|---|---|---|---|

## Layout
- Section 1:
- Section 2:

## Filters and Drilldowns
- Global filters:
- Local filters:
- Drill paths:

## Validation
- Reconciliation method:
- Edge cases tested:
- Known caveats:

## Usage Notes
- Interpretation guidance
- Anti-patterns to avoid
```

---

## `templates/release_checklist.md`

```md
# Release Checklist

## Artifacts
- [ ] Intake completed
- [ ] Data contract approved
- [ ] Model spec approved
- [ ] Pipeline spec completed
- [ ] Test plan evidence attached
- [ ] Dashboard spec completed

## Gates
- [ ] Architect -> Engineer PASS
- [ ] Engineer -> BI PASS
- [ ] BI -> Coordinator PASS

## Quality
- [ ] KPI glossary alignment verified
- [ ] Freshness/SLA verified
- [ ] Known caveats documented

## Readiness
- [ ] Stakeholder review completed
- [ ] Rollback/mitigation plan defined
- [ ] Final coordinator decision: READY
```

---

## `standards/naming_conventions.md`

```md
# Naming Conventions

## General
- Use snake_case for dataset and field names
- Use explicit names over abbreviations
- Avoid reserved keywords

## Layer Prefixes
- bronze_<domain>_<entity>
- silver_<domain>_<entity>
- gold_<domain>_<subject>

## Key Fields
- Primary keys: <entity>_id
- Foreign keys: <parent_entity>_id
- Timestamps: created_at, updated_at, event_at

## KPI Naming
- kpi_<business_term>
- Ratio metrics end with _rate or _pct
```

---

## `standards/layer_definitions.md`

```md
# Layer Definitions

## Bronze
Raw, append-friendly ingestion zone.
- Minimal transformation
- Preserve source fidelity
- Add ingestion metadata only

## Silver
Conformed and cleaned integration layer.
- Typing, dedup, standardization
- Rule-based cleansing
- Entity-level consistency

## Gold
Business-serving analytics layer.
- Curated for KPIs and dashboards
- Stable semantic meaning
- Optimized for consumption
```

---

## `standards/kpi_glossary.md`

```md
# KPI Glossary

## Required Fields per KPI
- Name
- Business definition
- Formula
- Grain
- Dimensions
- Source gold model
- Owner
- Caveats

## Governance Rules
- KPI formulas require owner approval
- No dashboard KPI without glossary entry
- Any formula change must include version/date
```

---

## `standards/testing_policy.md`

```md
# Testing Policy

## Mandatory Tests
- Not-null on required columns
- Uniqueness on declared keys
- Referential integrity on FK relations
- Freshness checks on critical datasets

## Severity
- Critical: blocks release
- High: release only with coordinator exception
- Medium/Low: tracked with remediation date

## Evidence
- Every release must include test run summary
- Failures need owner + ETA
```

---

## `standards/sla_freshness_policy.md`

```md
# SLA and Freshness Policy

## SLA Tiers
- Tier 1 (critical): <X hours max latency>
- Tier 2 (important): <Y hours>
- Tier 3 (standard): <Z hours>

## Freshness Contract
- Dataset owner must define expected update cadence
- Missed freshness window triggers incident workflow

## Incident Handling
- Detect -> Notify -> Triage -> Mitigate -> Postmortem
```

---

## `gates/architect_to_engineer.md`

```md
# Gate: Architect -> Engineer

## Pass Criteria
- [ ] Business grain explicitly defined
- [ ] Primary and foreign keys defined
- [ ] Source-to-target mapping complete
- [ ] SCD strategy documented
- [ ] DQ rules are testable
- [ ] Open questions resolved or escalated

## Fail Conditions
- Missing grain/keys
- Ambiguous business rules
- Untestable quality constraints
```

---

## `gates/engineer_to_bi.md`

```md
# Gate: Engineer -> BI

## Pass Criteria
- [ ] Gold datasets available and documented
- [ ] Mandatory tests passed
- [ ] Freshness checks pass or approved exception exists
- [ ] Join guidance for BI included
- [ ] Known caveats documented

## Fail Conditions
- Failing critical tests
- No gold documentation
- Missing caveat disclosure
```

---

## `gates/bi_to_coordinator.md`

```md
# Gate: BI -> Coordinator

## Pass Criteria
- [ ] KPI formulas align with glossary
- [ ] Reconciliation checks documented
- [ ] Filter/drilldown behavior validated
- [ ] Edge-case behavior reviewed
- [ ] Stakeholder narrative included

## Fail Conditions
- KPI mismatch with glossary
- Unverified interactions
- Missing validation evidence
```

---

## How to run this in Claude Code (exact sequence)

Use these prompts in order:

1. **Bootstrap**
   - “Act as Coordinator. Using `templates/intake.md`, collect missing details for request: `<your request>`.”

2. **Architecture**
   - “Act as Data Architect. Produce `data_contract` and `model_spec` outputs using our standards.”

3. **Engineering**
   - “Act as Data Engineer. From approved model spec, produce `pipeline_spec`, `test_plan`, and BI handoff.”

4. **BI**
   - “Act as BI Specialist. From gold outputs and KPI glossary, produce dashboard spec and validation notes.”

5. **Coordinator close**
   - “Run all three gate checklists and issue final READY/NOT READY decision with open risks.”

---

If you want, I can next give you a **single master coordinator prompt** that automatically orchestrates these 4 roles in one run (including gate enforcement and retry behavior).

