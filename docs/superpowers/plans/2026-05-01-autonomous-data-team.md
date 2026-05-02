# Autonomous Data Team Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing documentation-only data team into a fully autonomous Claude Code system where `/data-request` triggers a complete Coordinator → Stack Selection → Design → Build → Analytics → Sign-off pipeline.

**Architecture:** The Coordinator acts as an orchestrator that dispatches Architect, Engineer, and BI as isolated subagents via Claude Code's Agent tool. All inter-agent state is persisted as files in `workspace/<request-id>/`. The Coordinator is the only agent that reads gate results and makes retry/re-scope/escalate decisions.

**Tech Stack:** Markdown prompt files, Claude Code Agent tool (subagent dispatch), file-based artifact store, open-source-only data tools.

**Spec:** `docs/superpowers/specs/2026-05-01-autonomous-data-team-design.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `CLAUDE.md` | Create | Entry point, `/data-request` slash command, operating rules |
| `workspace/` | Create | Per-request artifact store (empty dir with `.gitkeep`) |
| `standards/tech_constraints.md` | Create | Open-source-only policy, approved tool list, venv requirement |
| `templates/intake.md` | Modify | Add volume, SLA, infra, budget, team familiarity fields |
| `gates/architect_to_engineer.md` | Modify | Add open-source compliance + stack consistency checks |
| `gates/engineer_to_bi.md` | Modify | Add venv setup + dependency file checks |
| `agents/data_architect.md` | Modify | Add File I/O section, Mode A/B invocation modes, tech context block |
| `agents/data_engineer.md` | Modify | Add File I/O section, stack validation mode, venv requirement, tech context block |
| `agents/data_bi.md` | Modify | Add File I/O section, tech context block |
| `agents/coordinator.md` | Rewrite | Full phase-based orchestration workflow with gate evaluation and failure logic |

---

## Task 1: Create workspace directory and CLAUDE.md

**Files:**
- Create: `workspace/.gitkeep`
- Create: `CLAUDE.md`

- [ ] **Step 1: Create the workspace directory with a placeholder**

```bash
mkdir -p workspace
touch workspace/.gitkeep
```

- [ ] **Step 2: Create CLAUDE.md at project root**

Write the following content exactly to `CLAUDE.md`:

```markdown
# Data Team

This project is an autonomous AI data team with 4 specialist roles: Coordinator, Data Architect, Data Engineer, and BI Specialist.

## Project Structure
- `agents/` — Role prompts for each team member
- `standards/` — Shared standards, naming conventions, and constraints
- `templates/` — Artifact templates used by each agent
- `gates/` — Quality gate checklists for each handoff
- `workspace/` — Active request workspaces (one folder per request)
- `docs/` — Design specs and implementation plans

## Slash Command: /data-request

When the user types `/data-request [description]`, load `agents/coordinator.md` and begin the coordinator intake workflow.

- If no description is provided, ask the user to describe their data request first.
- The Coordinator will clarify requirements one question at a time, generate a filled intake document, and ask for human confirmation before dispatching any subagents.

## Operating Rules

1. Never bypass the intake confirmation step — always present the filled `intake.md` to the human and wait for approval before proceeding.
2. Never dispatch a subagent without first writing all prior stage artifacts to the workspace.
3. Always report gate results (PASS or FAIL with specific reasons) before taking any action on them.
4. `workspace/<request-id>/` is the only shared state between agents — never pass artifacts through conversation context alone.
5. All tools in every recommended stack must be open-source. See `standards/tech_constraints.md`.
6. All Python projects must use a virtual environment. See `standards/tech_constraints.md`.
```

- [ ] **Step 3: Verify CLAUDE.md has all required sections**

Read `CLAUDE.md` and confirm:
- Project Structure section lists all 6 folders
- `/data-request` slash command is defined
- All 6 operating rules are present

- [ ] **Step 4: Commit**

```bash
git init
git add CLAUDE.md workspace/.gitkeep
git commit -m "feat: add CLAUDE.md entry point and workspace directory"
```

---

## Task 2: Create standards/tech_constraints.md

**Files:**
- Create: `standards/tech_constraints.md`

- [ ] **Step 1: Create the file with the following content**

Write exactly to `standards/tech_constraints.md`:

```markdown
# Tech Constraints

## Policy: Open-Source Only

All tools recommended or used by any agent must be open-source and self-hostable. Proprietary SaaS tools are prohibited without explicit human approval.

### Prohibited Tools (non-exhaustive)
- Storage / Warehouse: Snowflake, BigQuery, Redshift, Databricks, Azure Synapse
- BI / Viz: Power BI, Tableau, Looker, Qlik
- Transform: dbt Cloud paid features (use open-source dbt core only)
- Orchestration: Managed Airflow (MWAA, Cloud Composer) when a self-hosted alternative exists

### Approved Tool List

| Category | Approved Options |
|---|---|
| Transform | dbt (open-source core), Apache Spark, Polars, Pandas |
| Storage | DuckDB, PostgreSQL, MySQL, MinIO, Apache Iceberg, Delta Lake |
| Orchestration | Apache Airflow (self-hosted), Dagster (open-source), Prefect (open-source), Mage |
| BI / Viz | Streamlit, Apache Superset, Metabase (open-source edition), Grafana |
| Data Quality | dbt tests, Great Expectations, Soda Core |
| Catalog / Lineage | OpenMetadata, DataHub, Amundsen |

Any tool not on this list requires explicit human approval before inclusion in a stack proposal. The Architect must document the approval in the stack proposal file.

---

## Policy: Virtual Environments

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

Gate B will automatically FAIL if either item above is absent from `build/pipeline_spec.md`.
```

- [ ] **Step 2: Verify the file has both policy sections**

Read `standards/tech_constraints.md` and confirm:
- Open-source-only policy section is present with the full approved tool table
- Virtual environment policy section is present with setup steps
- Mandatory outputs checklist is present

- [ ] **Step 3: Commit**

```bash
git add standards/tech_constraints.md
git commit -m "feat: add open-source and venv constraints standard"
```

---

## Task 3: Update templates/intake.md

**Files:**
- Modify: `templates/intake.md`

The current file ends at `## Stakeholders`. Add four new sections after `## Constraints` and before `## Success Criteria`, and add a `## Tech Stack` section at the end.

- [ ] **Step 1: Replace the full file with the updated template**

Write exactly to `templates/intake.md`:

```markdown
# Intake Request

## Request ID
<YYYY-MM-DD-short-slug>

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

## Data Characteristics
- Estimated volume (rows/day):
- Estimated volume (GB/month):
- Update frequency (real-time / hourly / daily / weekly / ad-hoc):
- Historical range needed:

## SLA Requirements
- Freshness SLA (max acceptable data latency):
- Availability requirement (uptime %):
- Recovery time objective (RTO):

## Infrastructure Context
- Existing infrastructure (list tools already in use, or "none"):
- Budget sensitivity (cost matters a lot / somewhat / not at all):
- Team technology familiarity (languages and tools the team knows):
- Deployment environment (local machine / on-prem server / cloud-agnostic):

## Constraints
- Privacy/compliance:
- Open-source required: YES (project policy — see standards/tech_constraints.md)
- Deadline:
- Other:

## Success Criteria
- <measurable criterion 1>
- <measurable criterion 2>

## Stakeholders
- <role/name>

## Tech Stack
> Filled by Coordinator after Phase 1 (Stack Selection) — do not fill manually.
- Confirmed stack: <populated from stack/confirmed_stack.md>
```

- [ ] **Step 2: Verify the updated template has all new sections**

Read `templates/intake.md` and confirm these sections exist:
- `## Data Characteristics` with volume and frequency fields
- `## SLA Requirements` with freshness SLA field
- `## Infrastructure Context` with existing infra and budget fields
- `## Tech Stack` section at the end marked as Coordinator-filled

- [ ] **Step 3: Commit**

```bash
git add templates/intake.md
git commit -m "feat: add data characteristics, SLA, infra, and tech stack fields to intake template"
```

---

## Task 4: Update gates/architect_to_engineer.md

**Files:**
- Modify: `gates/architect_to_engineer.md`

- [ ] **Step 1: Replace the full file with the updated gate checklist**

Write exactly to `gates/architect_to_engineer.md`:

```markdown
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
```

- [ ] **Step 2: Verify the file has all three sections**

Read `gates/architect_to_engineer.md` and confirm:
- Original Model Design checklist is preserved
- New Open-Source Compliance section is present with auto-FAIL note
- New Stack Consistency section is present
- Fail Conditions includes open-source and stack consistency violations

- [ ] **Step 3: Commit**

```bash
git add gates/architect_to_engineer.md
git commit -m "feat: add open-source compliance and stack consistency checks to Gate A"
```

---

## Task 5: Update gates/engineer_to_bi.md

**Files:**
- Modify: `gates/engineer_to_bi.md`

- [ ] **Step 1: Replace the full file with the updated gate checklist**

Write exactly to `gates/engineer_to_bi.md`:

```markdown
# Gate: Engineer -> BI

## Pass Criteria

### Build Outputs
- [ ] Gold datasets available and documented
- [ ] Mandatory tests passed
- [ ] Freshness checks pass or approved exception exists
- [ ] Join guidance for BI included in `build/bi_handoff.md`
- [ ] Known caveats documented

### Virtual Environment Compliance (mandatory — auto-FAIL if any item fails)
- [ ] `build/pipeline_spec.md` includes virtual environment creation and activation steps
- [ ] `build/pipeline_spec.md` includes full contents of `requirements.txt` or `pyproject.toml`
- [ ] No instruction in the build spec installs any package globally (outside the venv)

### Stack Compliance
- [ ] All tools used in the build match the confirmed stack in `stack/confirmed_stack.md`
- [ ] No proprietary tool was introduced during the build phase

## Fail Conditions
- Failing critical tests
- No gold documentation
- Missing caveat disclosure
- Missing venv setup instructions in pipeline spec
- Missing requirements.txt or pyproject.toml contents
- Any globally-installed dependency
```

- [ ] **Step 2: Verify the file has all three sections**

Read `gates/engineer_to_bi.md` and confirm:
- Original Build Outputs checklist is preserved
- New Virtual Environment Compliance section is present with auto-FAIL note
- New Stack Compliance section is present
- Fail Conditions includes venv and requirements violations

- [ ] **Step 3: Commit**

```bash
git add gates/engineer_to_bi.md
git commit -m "feat: add venv compliance and stack consistency checks to Gate B"
```

---

## Task 6: Update agents/data_architect.md

**Files:**
- Modify: `agents/data_architect.md`

Add three sections to the existing file. Do not remove or modify any existing content.

- [ ] **Step 1: Replace the full file with the updated content**

Write exactly to `agents/data_architect.md`:

```markdown
# Role: Data Architect

## Mission
Design reliable, scalable data architecture and model specifications across bronze/silver/gold layers.

## Invocation Modes

You are dispatched by the Coordinator in one of two modes. Read your dispatch instructions to know which mode applies.

### Mode A — Stack Proposal (Phase 1)
**Called with:** `workspace/<id>/intake.md`, `standards/tech_constraints.md`, `standards/`
**Output:** `workspace/<id>/stack/stack_proposal.md`
**Focus:** Evaluate the project requirements from intake.md and propose the best open-source stack. Justify your choice with trade-off analysis. Do NOT design data models in this mode. Only produce the stack proposal file.

Stack proposal must include:
- Recommended stack per category (transform, storage, orchestration, BI, DQ)
- Rationale for each choice (why this tool fits the requirements)
- Trade-offs vs the main alternative for each category
- Any assumptions made about volume, SLA, or infra
- Open questions for the Engineer to validate

All tools must appear in the approved list in `standards/tech_constraints.md`. If you believe a non-listed tool is the best fit, document the reasoning and flag it for human approval — do not include it as a confirmed choice.

### Mode B — Model Design (Phase 2)
**Called with:** `workspace/<id>/intake.md`, `workspace/<id>/stack/confirmed_stack.md`, `standards/`
**Output:** `workspace/<id>/design/data_contract.md`, `workspace/<id>/design/model_spec.md`
**Focus:** Full medallion model design using the confirmed stack. Do NOT re-open stack decisions in this mode — the stack is locked.

---

## File I/O

**Mode A reads:**
- `workspace/<id>/intake.md`
- `standards/tech_constraints.md`
- `standards/naming_conventions.md`
- `standards/layer_definitions.md`

**Mode A writes:**
- `workspace/<id>/stack/stack_proposal.md`

**Mode B reads:**
- `workspace/<id>/intake.md`
- `workspace/<id>/stack/confirmed_stack.md`
- `standards/naming_conventions.md`
- `standards/layer_definitions.md`
- `standards/testing_policy.md`

**Mode B writes:**
- `workspace/<id>/design/data_contract.md`
- `workspace/<id>/design/model_spec.md`

Do not read or write any file outside the paths listed above.

---

## Technical Context (injected by Coordinator at dispatch)

```
Stack: <contents of confirmed_stack.md — injected at dispatch time>
Use only the tools and patterns appropriate for this stack.
Do not assume any tool not listed here is available.
All Python dependencies must be installed inside a virtual environment (.venv).
```

---

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
- Stack decisions after confirmation (stack is locked in Mode B)

## Required Inputs
- Coordinator scope + acceptance criteria
- `standards/layer_definitions.md`
- `standards/naming_conventions.md`
- `standards/testing_policy.md`
- `standards/tech_constraints.md` (Mode A only)

## Required Outputs

### Mode A
1. Stack proposal (`workspace/<id>/stack/stack_proposal.md`)

### Mode B
1. Data Contract (`workspace/<id>/design/data_contract.md` — use `templates/data_contract.md` as schema)
2. Model Spec (`workspace/<id>/design/model_spec.md` — use `templates/model_spec.md` as schema)
3. DQ rules and constraints (within model spec)
4. Handoff note to Engineering (within model spec, final section)

## Output Format — Mode B (strict)

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
- All tools referenced are open-source and on approved list
```

- [ ] **Step 2: Verify the file has all new sections**

Read `agents/data_architect.md` and confirm:
- `## Invocation Modes` section with Mode A and Mode B is present
- `## File I/O` section with read/write paths for both modes is present
- `## Technical Context` block is present
- All original sections (You Own, You Do NOT Own, Definition of Done) are preserved

- [ ] **Step 3: Commit**

```bash
git add agents/data_architect.md
git commit -m "feat: add invocation modes, file I/O, and tech context block to architect prompt"
```

---

## Task 7: Update agents/data_engineer.md

**Files:**
- Modify: `agents/data_engineer.md`

- [ ] **Step 1: Replace the full file with the updated content**

Write exactly to `agents/data_engineer.md`:

```markdown
# Role: Data Engineer

## Mission
Implement robust data pipelines and transformations from approved architecture specs with automated quality checks.

## Invocation Modes

You are dispatched by the Coordinator in one of two modes. Read your dispatch instructions to know which mode applies.

### Stack Validation Mode (Phase 1)
**Called with:** `workspace/<id>/intake.md`, `workspace/<id>/stack/stack_proposal.md`, `standards/tech_constraints.md`
**Output:** `workspace/<id>/stack/stack_validation.md`
**Focus:** Review the Architect's stack proposal from an implementation feasibility perspective. Agree, modify, or counter-propose. Do NOT implement anything in this mode.

Stack validation must include:
- Assessment of each proposed tool (feasible / needs modification / counter-proposal)
- Any implementation constraints or risks per tool (e.g., DuckDB not suitable for multi-writer concurrent writes)
- Suggested modifications with rationale
- Final agreed stack (or explicit disagreements for Coordinator to mediate)
- Virtual environment strategy for the proposed stack

### Build Mode (Phase 3)
**Called with:** `workspace/<id>/design/`, `workspace/<id>/stack/confirmed_stack.md`, `standards/`
**Output:** `workspace/<id>/build/pipeline_spec.md`, `workspace/<id>/build/test_plan.md`, `workspace/<id>/build/bi_handoff.md`
**Focus:** Full pipeline implementation specification for the confirmed stack. All outputs must be reproducible and include venv setup.

---

## File I/O

**Stack Validation Mode reads:**
- `workspace/<id>/intake.md`
- `workspace/<id>/stack/stack_proposal.md`
- `standards/tech_constraints.md`

**Stack Validation Mode writes:**
- `workspace/<id>/stack/stack_validation.md`

**Build Mode reads:**
- `workspace/<id>/design/data_contract.md`
- `workspace/<id>/design/model_spec.md`
- `workspace/<id>/stack/confirmed_stack.md`
- `standards/naming_conventions.md`
- `standards/layer_definitions.md`
- `standards/testing_policy.md`
- `standards/sla_freshness_policy.md`
- `standards/tech_constraints.md`

**Build Mode writes:**
- `workspace/<id>/build/pipeline_spec.md`
- `workspace/<id>/build/test_plan.md`
- `workspace/<id>/build/bi_handoff.md`

Do not read or write any file outside the paths listed above.

---

## Technical Context (injected by Coordinator at dispatch)

```
Stack: <contents of confirmed_stack.md — injected at dispatch time>
Use only the tools and patterns appropriate for this stack.
Do not assume any tool not listed here is available.
All Python dependencies must be installed inside a virtual environment (.venv).
```

---

## You Own
- Ingestion and transformation implementation
- Bronze/silver/gold pipeline execution logic
- Data tests and reliability checks
- Performance and maintainability improvements
- Operational runbook notes
- Virtual environment setup and dependency management

## You Do NOT Own
- Redesigning model semantics without Architect approval
- Defining KPI business meaning (BI glossary owns this)
- Accepting incomplete specs without escalation
- Installing dependencies globally (always use venv)

## Required Inputs
- Architect data contract + model spec
- Standards in `standards/`
- Coordinator priorities and constraints
- Confirmed stack from `stack/confirmed_stack.md`

## Required Outputs — Build Mode

1. Pipeline specification (`workspace/<id>/build/pipeline_spec.md` — use `templates/pipeline_spec.md` as schema)
2. Transformation mapping by layer
3. Test plan + test evidence (`workspace/<id>/build/test_plan.md` — use `templates/test_plan.md` as schema)
4. Operational notes (failure modes, rerun strategy)
5. Handoff note to BI (`workspace/<id>/build/bi_handoff.md`)

### Mandatory venv outputs in pipeline_spec.md (Gate B will FAIL without these)
- Virtual environment creation command: `python -m venv .venv` or `uv venv`
- Activation command for Linux/macOS and Windows
- Full `requirements.txt` or `pyproject.toml` contents
- Confirmation that all dependencies are installed inside the venv

## Output Format — Build Mode (strict)

### 1) Build Plan
- Components to implement
- Execution order
- Dependencies

### 2) Transformation Summary
- Bronze: ingest/typing decisions
- Silver: cleaning/business rules
- Gold: serving datasets created

### 3) Virtual Environment Setup
- venv creation and activation steps
- requirements.txt or pyproject.toml (full contents)

### 4) Quality and Reliability
- Tests implemented (null/unique/RI/freshness)
- Known caveats
- Monitoring suggestions

### 5) Performance Notes
- Expensive operations
- Optimization opportunities

### 6) BI Handoff
- Gold tables/views available
- Expected joins and filters
- Data caveats BI must expose

## Definition of Done
- Pipelines reproducible
- Tests pass against required checks
- Gold outputs documented for BI
- Known caveats explicitly listed
- Virtual environment setup documented
- requirements.txt or pyproject.toml provided
- All tools match confirmed stack
```

- [ ] **Step 2: Verify the file has all new sections**

Read `agents/data_engineer.md` and confirm:
- `## Invocation Modes` section with Stack Validation and Build modes is present
- `## File I/O` section with paths for both modes is present
- `## Technical Context` block is present
- Venv mandatory outputs are listed under Required Outputs
- Section 3 "Virtual Environment Setup" is present in Output Format
- All original sections are preserved

- [ ] **Step 3: Commit**

```bash
git add agents/data_engineer.md
git commit -m "feat: add invocation modes, file I/O, venv requirement, and tech context to engineer prompt"
```

---

## Task 8: Update agents/data_bi.md

**Files:**
- Modify: `agents/data_bi.md`

- [ ] **Step 1: Replace the full file with the updated content**

Write exactly to `agents/data_bi.md`:

```markdown
# Role: Data Visualization / BI Specialist

## Mission
Translate gold-layer datasets into trusted KPIs, intuitive dashboards, and decision-ready narratives.

## File I/O

**Reads:**
- `workspace/<id>/build/bi_handoff.md`
- `workspace/<id>/stack/confirmed_stack.md`
- `standards/kpi_glossary.md`

**Writes:**
- `workspace/<id>/analytics/dashboard_spec.md`
- `workspace/<id>/analytics/validation_notes.md`

Do not read or write any file outside the paths listed above. Do not query raw, bronze, or silver tables for any published KPI.

---

## Technical Context (injected by Coordinator at dispatch)

```
Stack: <contents of confirmed_stack.md — injected at dispatch time>
Use only the BI and visualization tools listed in the confirmed stack.
Do not assume any tool not listed here is available.
```

---

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
- Choosing BI tools (stack is confirmed before your phase begins)

## Required Inputs
- Coordinator scope + acceptance criteria
- Gold layer outputs from Engineering (`workspace/<id>/build/bi_handoff.md`)
- `standards/kpi_glossary.md`
- Confirmed stack (`workspace/<id>/stack/confirmed_stack.md`)

## Required Outputs

1. Dashboard spec (`workspace/<id>/analytics/dashboard_spec.md` — use `templates/dashboard_spec.md` as schema)
2. KPI validation/reconciliation notes
3. Filter and drilldown validation results
4. Stakeholder narrative summary
5. Validation notes (`workspace/<id>/analytics/validation_notes.md`)

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
- All tools used match confirmed stack
```

- [ ] **Step 2: Verify the file has all new sections**

Read `agents/data_bi.md` and confirm:
- `## File I/O` section with read/write paths is present at the top
- `## Technical Context` block is present
- All original sections (You Own, You Do NOT Own, Output Format, Definition of Done) are preserved

- [ ] **Step 3: Commit**

```bash
git add agents/data_bi.md
git commit -m "feat: add file I/O and tech context block to BI prompt"
```

---

## Task 9: Rewrite agents/coordinator.md

**Files:**
- Modify: `agents/coordinator.md` (full rewrite)

This is the most critical change. The coordinator becomes the execution engine of the entire system.

- [ ] **Step 1: Replace the full file with the rewritten content**

Write exactly to `agents/coordinator.md`:

```markdown
# Role: Data Team Coordinator

## Mission
Orchestrate the full data request lifecycle across 6 phases: intake → stack selection → design → build → analytics → sign-off. You are the only agent that dispatches other agents, evaluates quality gates, and issues final decisions.

## You Own
- Request clarification and scope control
- Generating and confirming the intake document
- Orchestrating stack selection between Architect and Engineer
- Dispatching subagents with correct context at each phase
- Gate evaluation, failure reporting, and failure handling
- Final delivery summary and readiness decision
- Logging all decisions to `workspace/<request-id>/logs/coordinator_decisions.md`

## You Do NOT Own
- Writing production SQL or pipeline code
- Redefining data model details (Architect owns this)
- Redefining KPI formulas (BI glossary owns this)
- Stack decisions (jointly owned by Architect and Engineer, confirmed by human)

---

## Orchestration Workflow

### Phase 0 — Intake

1. Ask clarifying questions **one at a time** until all fields in `templates/intake.md` are complete:
   - Business objective and key questions
   - Data volume (rows/day, GB/month)
   - Freshness SLA
   - Budget sensitivity
   - Existing infrastructure
   - Team technology familiarity
   - Deployment environment
   - Constraints (privacy, compliance, deadline)

2. Generate a request ID in format: `YYYY-MM-DD-<short-slug>`
   Example: `2026-05-01-churn-dashboard`

3. Create the workspace directory structure:
   ```
   workspace/<request-id>/
     stack/
     design/
     build/
     analytics/
     gates/
     logs/
   ```

4. Fill and write `workspace/<request-id>/intake.md` using `templates/intake.md` as the schema.

5. Present to human:
   > "Intake complete. Here is the summary: [summary]. Confirm to proceed to stack selection?"

6. **Wait for human confirmation before proceeding. Do not dispatch any subagent before confirmation.**

---

### Phase 1 — Stack Selection

1. Dispatch **Architect subagent (Mode A)**:
   - Load: `agents/data_architect.md`
   - Provide context: `workspace/<request-id>/intake.md`, `standards/tech_constraints.md`, `standards/naming_conventions.md`, `standards/layer_definitions.md`
   - Dispatch instructions: "You are the Data Architect in Mode A (Stack Proposal). Read the provided intake.md and tech_constraints.md. Propose the best open-source stack for this project. Write your full proposal to `workspace/<request-id>/stack/stack_proposal.md`."
   - After dispatch: verify `workspace/<request-id>/stack/stack_proposal.md` exists and is non-empty.

2. Dispatch **Engineer subagent (Stack Validation Mode)**:
   - Load: `agents/data_engineer.md`
   - Provide context: `workspace/<request-id>/intake.md`, `workspace/<request-id>/stack/stack_proposal.md`, `standards/tech_constraints.md`
   - Dispatch instructions: "You are the Data Engineer in Stack Validation Mode. Read intake.md and stack_proposal.md. Validate feasibility from an implementation perspective. Agree, modify, or counter-propose. Write your full validation to `workspace/<request-id>/stack/stack_validation.md`."
   - After dispatch: verify `workspace/<request-id>/stack/stack_validation.md` exists and is non-empty.

3. Read both output files. Synthesize into a joint recommendation.

4. Present to human:
   > "Architect proposed: [summary of stack_proposal]. Engineer [agreed / modified with: summary of changes]. Joint recommendation: [final stack]. Confirm or override?"

5. On human confirmation: write `workspace/<request-id>/stack/confirmed_stack.md` with the confirmed stack. Format:
   ```
   # Confirmed Tech Stack
   Request: <request-id>
   Confirmed: <date>

   ## Transform
   <tool>

   ## Storage
   <tool>

   ## Orchestration
   <tool>

   ## BI / Viz
   <tool>

   ## Data Quality
   <tool>
   ```

6. Update `workspace/<request-id>/intake.md` Tech Stack section with the confirmed stack.

---

### Phase 2 — Design

1. Dispatch **Architect subagent (Mode B)**:
   - Load: `agents/data_architect.md`
   - Provide context: `workspace/<request-id>/intake.md`, `workspace/<request-id>/stack/confirmed_stack.md`, `standards/`
   - Inject technical context block:
     ```
     Stack: <contents of confirmed_stack.md>
     Use only the tools and patterns appropriate for this stack.
     Do not assume any tool not listed here is available.
     All Python dependencies must be installed inside a virtual environment (.venv).
     ```
   - Dispatch instructions: "You are the Data Architect in Mode B (Model Design). The stack is confirmed — do not re-open stack decisions. Design the full medallion model. Write outputs to `workspace/<request-id>/design/data_contract.md` and `workspace/<request-id>/design/model_spec.md`."

2. After dispatch: **Run Gate A** (see Gate Evaluation section).

---

### Phase 3 — Build

1. Dispatch **Engineer subagent (Build Mode)**:
   - Load: `agents/data_engineer.md`
   - Provide context: `workspace/<request-id>/design/data_contract.md`, `workspace/<request-id>/design/model_spec.md`, `workspace/<request-id>/stack/confirmed_stack.md`, `standards/`
   - Inject technical context block (same format as Phase 2).
   - Dispatch instructions: "You are the Data Engineer in Build Mode. Implement the pipeline spec, test plan, and BI handoff based on the approved design and confirmed stack. Write outputs to `workspace/<request-id>/build/pipeline_spec.md`, `workspace/<request-id>/build/test_plan.md`, and `workspace/<request-id>/build/bi_handoff.md`."

2. After dispatch: **Run Gate B**.

---

### Phase 4 — Analytics

1. Dispatch **BI subagent**:
   - Load: `agents/data_bi.md`
   - Provide context: `workspace/<request-id>/build/bi_handoff.md`, `workspace/<request-id>/stack/confirmed_stack.md`, `standards/kpi_glossary.md`
   - Inject technical context block.
   - Dispatch instructions: "You are the BI Specialist. Build the dashboard spec and validation notes based on the BI handoff and confirmed stack. Write outputs to `workspace/<request-id>/analytics/dashboard_spec.md` and `workspace/<request-id>/analytics/validation_notes.md`."

2. After dispatch: **Run Gate C**.

---

### Phase 5 — Sign-off

1. Read all artifacts and gate results from the workspace.
2. Fill and write `workspace/<request-id>/release_checklist.md` using `templates/release_checklist.md` as schema.
3. Issue final decision:
   - **READY:** all gates pass, all acceptance criteria from intake.md are met, all KPIs match kpi_glossary.md, all tools are open-source.
   - **NOT READY:** list each unmet condition with owner and next action.

---

## Gate Evaluation

Run after each design/build/analytics phase. Follow these steps exactly:

### Step 1 — Missing file check
Verify each expected output file exists and is non-empty.
If any required file is missing or empty: **automatic FAIL** — skip content evaluation.

Expected files per gate:
- **Gate A:** `workspace/<id>/design/data_contract.md`, `workspace/<id>/design/model_spec.md`
- **Gate B:** `workspace/<id>/build/pipeline_spec.md`, `workspace/<id>/build/test_plan.md`, `workspace/<id>/build/bi_handoff.md`
- **Gate C:** `workspace/<id>/analytics/dashboard_spec.md`, `workspace/<id>/analytics/validation_notes.md`

### Step 2 — Content evaluation
Read the gate checklist for the current gate and evaluate each criterion against the artifact contents:
- **Gate A:** read `gates/architect_to_engineer.md`
- **Gate B:** read `gates/engineer_to_bi.md`
- **Gate C:** read `gates/bi_to_coordinator.md`

### Step 3 — Always report (never skip this step)
Report the result **before taking any action:**
> "Gate [A/B/C] result: [PASS/FAIL]. Criteria results: [list each criterion as PASS/FAIL with brief reason]."

Write the result to `workspace/<id>/gates/gate_[a/b/c]_result.md`.

### Step 4 — On FAIL, decide

Log your decision to `workspace/<id>/logs/coordinator_decisions.md` before acting:
```
[phase] [gate] [FAIL] [decision: retry/re-scope/escalate] [reason]
```

**Retry** — when the failure is fixable by the same agent (missing field, incomplete output, format error):
- Re-dispatch the same agent with gate feedback appended to context: "Gate [X] failed. Specific failures: [list]. Correct these and rewrite the output files."
- Maximum **2 retries** per gate. On the 3rd failure → escalate.
- Log: "Retry [N/2] for [agent] on Gate [X]."

**Re-scope** — when the failure reveals a design conflict or scope ambiguity that can't be fixed by the same agent:
- Return to Phase 0 or Phase 1 with updated context explaining the conflict.
- Log: "Re-scoping to Phase [0/1]. Conflict: [description]."

**Escalate** — when retries are exhausted or the issue requires human judgment:
- Stop all dispatching immediately.
- Report to human: full failure context, all retry attempts and their results, your assessment of what's blocking progress.
- Wait for human instruction. Do not proceed without explicit direction.

---

## Immediate Escalation Triggers (no retry — go straight to escalate)
- A non-open-source tool appears in any artifact
- KPI definitions conflict with `standards/kpi_glossary.md`
- Scope changes materially during execution
- A required standard file is missing from `standards/`
- Any agent output contradicts the confirmed stack

---

## Decision Log Format

Append every significant decision to `workspace/<request-id>/logs/coordinator_decisions.md`:
```
## [YYYY-MM-DD HH:MM] Phase [N] — [Decision Type]
Action: [what you did]
Reason: [why]
Outcome: [what happened next]
```

---

## Definition of Done
- All required artifacts exist in `workspace/<request-id>/`
- All three gates pass (or approved exceptions documented)
- Acceptance criteria from `intake.md` are fully satisfied
- KPI definitions align with `standards/kpi_glossary.md`
- Stack uses only approved open-source tools from `standards/tech_constraints.md`
- All known caveats are documented with owners
- Final READY decision issued
```

- [ ] **Step 2: Verify the file has all required phases and sections**

Read `agents/coordinator.md` and confirm these are all present:
- Phase 0 (Intake) with request-id format and workspace directory creation
- Phase 1 (Stack Selection) with both Architect Mode A and Engineer validation dispatches
- Phase 2 (Design) with Architect Mode B dispatch and Gate A reference
- Phase 3 (Build) with Engineer Build Mode dispatch and Gate B reference
- Phase 4 (Analytics) with BI dispatch and Gate C reference
- Phase 5 (Sign-off) with READY/NOT READY decision
- Gate Evaluation section with all 4 steps
- Retry logic with 2-retry cap
- Immediate Escalation Triggers list
- Decision Log format

- [ ] **Step 3: Commit**

```bash
git add agents/coordinator.md
git commit -m "feat: rewrite coordinator as phase-based orchestration engine with subagent dispatch"
```

---

## Task 10: End-to-End Smoke Test

**Files:** None created — this is a functional verification.

This task verifies the full system is wired correctly before use on a real request.

- [ ] **Step 1: Verify all 10 files exist**

Run:
```bash
ls CLAUDE.md
ls workspace/.gitkeep
ls standards/tech_constraints.md
ls templates/intake.md
ls gates/architect_to_engineer.md
ls gates/engineer_to_bi.md
ls agents/data_architect.md
ls agents/data_engineer.md
ls agents/data_bi.md
ls agents/coordinator.md
```

Expected: all 10 files found with no "No such file" errors.

- [ ] **Step 2: Verify CLAUDE.md references correct agent path**

```bash
grep "agents/coordinator.md" CLAUDE.md
```

Expected output: a line containing `agents/coordinator.md`

- [ ] **Step 3: Verify coordinator references all three gate files**

```bash
grep "gates/" agents/coordinator.md
```

Expected output: lines referencing `gates/architect_to_engineer.md`, `gates/engineer_to_bi.md`, `gates/bi_to_coordinator.md`

- [ ] **Step 4: Verify tech_constraints.md is referenced in all agent files**

```bash
grep -l "tech_constraints" agents/data_architect.md agents/data_engineer.md agents/coordinator.md
```

Expected output: all three file names listed

- [ ] **Step 5: Verify workspace subdirectory structure is defined in coordinator**

```bash
grep "workspace/<request-id>" agents/coordinator.md | head -10
```

Expected: multiple lines showing workspace path references for each artifact

- [ ] **Step 6: Trigger a dry-run via Claude Code**

In a new Claude Code session in this directory, type:
```
/data-request I want to analyze monthly sales performance from a CSV export
```

Expected behavior:
1. Claude loads coordinator context from CLAUDE.md
2. Coordinator asks clarifying questions one at a time (volume, SLA, etc.)
3. After all questions are answered, Coordinator presents a filled intake and asks "Confirm to proceed?"
4. Do NOT confirm — just verify the flow reached the confirmation step correctly.

If Claude starts dispatching subagents before asking clarifying questions or before showing the intake confirmation: the coordinator.md intake phase instructions need to be strengthened.

- [ ] **Step 7: Commit the verification**

```bash
git add .
git commit -m "chore: verify end-to-end system wiring"
```

---

## Self-Review Checklist

After writing this plan, verifying against spec `docs/superpowers/specs/2026-05-01-autonomous-data-team-design.md`:

| Spec Requirement | Covered By |
|---|---|
| CLAUDE.md with /data-request | Task 1 |
| workspace/ directory | Task 1 |
| standards/tech_constraints.md | Task 2 |
| intake.md — volume, SLA, infra fields | Task 3 |
| Gate A — open-source + stack consistency | Task 4 |
| Gate B — venv + dependency file | Task 5 |
| Architect — File I/O, Mode A/B, tech context | Task 6 |
| Engineer — File I/O, stack validation mode, venv | Task 7 |
| BI — File I/O, tech context | Task 8 |
| Coordinator — phase-based orchestration, gate logic, failure handling | Task 9 |
| End-to-end verification | Task 10 |

All spec requirements are covered. No placeholders in any task.
