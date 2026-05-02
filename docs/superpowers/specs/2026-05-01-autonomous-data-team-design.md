# Autonomous Data Team — Design Spec
**Date:** 2026-05-01  
**Status:** Approved  
**Approach:** B — File-based orchestration with true subagent dispatch

---

## 1. Problem Statement

The existing project has a solid documentation layer: 4 role prompts, 7 templates, 5 standards files, and 3 quality gate checklists. However, it has no execution engine. Agents cannot dispatch each other, artifacts cannot be shared between roles, there is no entry point for Claude Code, and the tech stack is either hardcoded or assumed to be known by the user.

The goal is to upgrade this into a fully autonomous data team where a single `/data-request` command triggers a complete Coordinator → Stack Selection → Design → Build → Analytics → Sign-off pipeline with no human intervention except at intake confirmation, stack confirmation, and gate escalation.

---

## 2. Scope

**In-scope:**
- CLAUDE.md entry point with `/data-request` slash command
- Coordinator rewrite as a phase-based orchestrator using subagent dispatch
- Architect and Engineer joint stack selection phase (sequential, Coordinator-mediated)
- `workspace/<request-id>/` as the shared artifact store across all agents
- Tech stack injection into every subagent dispatch (never hardcoded in role prompts)
- Gate logic executed by the Coordinator (read artifacts → evaluate → always report → decide)
- Gate failure handling: retry / re-scope / escalate with 2-retry cap
- Open-source-only constraint enforced at Architect proposal and Gate A
- Virtual environment requirement enforced at Engineer build and Gate B
- New standard: `standards/tech_constraints.md`
- Additive updates to 4 agent prompts and `templates/intake.md`

**Out-of-scope:**
- JSON state machine for crash-resumability (Approach C — future work)
- Parallel concurrent request management
- CI/CD integration
- External tool integrations (Slack notifications, GitHub PRs)

---

## 3. Architecture Overview

```
User: /data-request "describe the request"
         │
         ▼
   CLAUDE.md loads Coordinator context
         │
         ▼
   ── PHASE 0: INTAKE ──
   Coordinator clarifies one question at a time:
   volume, SLA, budget, existing infra, constraints
   → Writes: workspace/<id>/intake.md
   → Presents to human for confirmation
         │
         ▼ (confirmed)
   ── PHASE 1: STACK SELECTION ──
   Coordinator dispatches → Architect subagent (Mode A)
   (intake.md + standards/ + tech_constraints.md)
   → Writes: workspace/<id>/stack/stack_proposal.md

   Coordinator dispatches → Engineer subagent (stack mode)
   (intake.md + stack_proposal.md + standards/ + tech_constraints.md)
   → Writes: workspace/<id>/stack/stack_validation.md

   Coordinator synthesizes both outputs
   → Presents joint recommendation to human:
     "Architect proposed X. Engineer agreed/modified: Y. Final: Z. Confirm?"
   → On confirmation writes: workspace/<id>/stack/confirmed_stack.md
         │
         ▼ (confirmed)
   ── PHASE 2: DESIGN ──
   Coordinator dispatches → Architect subagent (Mode B)
   (intake.md + confirmed_stack.md + standards/)
   → Writes: workspace/<id>/design/data_contract.md
             workspace/<id>/design/model_spec.md

   Coordinator runs Gate A
   → Reads: design/ artifacts
   → Always reports: "Gate A: PASS/FAIL — [reasons]"
   → On fail: retry / re-scope / escalate
         │
         ▼ (Gate A passes)
   ── PHASE 3: BUILD ──
   Coordinator dispatches → Engineer subagent
   (design/ + confirmed_stack.md + standards/)
   → Writes: workspace/<id>/build/pipeline_spec.md
             workspace/<id>/build/test_plan.md
             workspace/<id>/build/bi_handoff.md

   Coordinator runs Gate B
   → Always reports → On fail: retry / re-scope / escalate
         │
         ▼ (Gate B passes)
   ── PHASE 4: ANALYTICS ──
   Coordinator dispatches → BI subagent
   (build/bi_handoff.md + confirmed_stack.md + standards/kpi_glossary.md)
   → Writes: workspace/<id>/analytics/dashboard_spec.md
             workspace/<id>/analytics/validation_notes.md

   Coordinator runs Gate C
   → Always reports → On fail: retry / re-scope / escalate
         │
         ▼ (Gate C passes)
   ── PHASE 5: SIGN-OFF ──
   Coordinator writes: workspace/<id>/release_checklist.md
   Issues: READY / NOT READY with full summary
```

---

## 4. Workspace Structure

Every request gets an isolated folder. No agent reads or writes outside its designated subfolders.

```
workspace/
  <YYYY-MM-DD-request-slug>/
    intake.md
    stack/
      stack_proposal.md        ← Architect (Mode A)
      stack_validation.md      ← Engineer (stack mode)
      confirmed_stack.md       ← Coordinator (after human confirmation)
    design/
      data_contract.md         ← Architect (Mode B)
      model_spec.md            ← Architect (Mode B)
    build/
      pipeline_spec.md         ← Engineer
      test_plan.md             ← Engineer
      bi_handoff.md            ← Engineer
    analytics/
      dashboard_spec.md        ← BI
      validation_notes.md      ← BI
    gates/
      gate_a_result.md         ← Coordinator
      gate_b_result.md         ← Coordinator
      gate_c_result.md         ← Coordinator
    logs/
      coordinator_decisions.md ← Coordinator (every decision + reason)
    release_checklist.md       ← Coordinator (final sign-off)
```

**Handoff contract — what each agent receives at dispatch:**

| Agent | Reads |
|---|---|
| Architect (Mode A — stack) | `intake.md`, `standards/`, `standards/tech_constraints.md` |
| Engineer (stack mode) | `intake.md`, `stack/stack_proposal.md`, `standards/tech_constraints.md` |
| Architect (Mode B — design) | `intake.md`, `stack/confirmed_stack.md`, `standards/` |
| Engineer (build mode) | `design/`, `stack/confirmed_stack.md`, `standards/` |
| BI | `build/bi_handoff.md`, `stack/confirmed_stack.md`, `standards/kpi_glossary.md` |
| Coordinator (gate evaluation) | all files in the relevant stage subfolder |

**Missing file rule:** if any expected output file is missing or empty after a subagent run, the Coordinator treats it as an automatic Gate FAIL before evaluating content.

---

## 5. CLAUDE.md Entry Point

New file at project root. Defines the slash command and operating rules.

**Contents:**
- Project description and folder map
- `/data-request [description]` — loads `agents/coordinator.md` and starts intake workflow
- Operating rules:
  - Never bypass the intake confirmation step
  - Never dispatch a subagent without writing prior stage artifacts first
  - Always report gate results before taking any action on them
  - `workspace/<request-id>/` is the only shared state between agents

---

## 6. Coordinator Rewrite

`agents/coordinator.md` is rewritten from a role description into a phase-based orchestration workflow. All existing ownership rules, escalation rules, and definition of done criteria are preserved.

**New structure:**
- Phase 0: Intake (clarify → fill template → confirm)
- Phase 1: Stack Selection (dispatch Architect Mode A → dispatch Engineer stack mode → synthesize → confirm)
- Phase 2: Design (dispatch Architect Mode B → Gate A)
- Phase 3: Build (dispatch Engineer build mode → Gate B)
- Phase 4: Analytics (dispatch BI → Gate C)
- Phase 5: Sign-off (release checklist → READY/NOT READY)

**Gate failure decision logic:**
```
Gate fails →
  1. Coordinator always reports: "Gate [X] FAILED. Reasons: [list]."
  2. Coordinator logs decision to coordinator_decisions.md
  3. Coordinator decides:
     - Retry: failure is fixable by the same agent (missing field, incomplete output)
               → Re-dispatch with gate feedback appended to context
               → Maximum 2 retries per gate; if 3rd fail → escalate
     - Re-scope: failure reveals a design conflict or scope issue
               → Return to Phase 0 or 1 with updated context
               → Log re-scope reason before restarting
     - Escalate: retries exhausted or issue requires human judgment
               → Stop, surface full context to human, wait for instruction
```

---

## 7. Agent Prompt Updates

All existing role boundaries, ownership rules, escalation rules, and definitions of done are preserved. Three sections are added to each prompt:

### 7.1 File I/O section
Each agent declares exactly which files to read and which files to write in the workspace. Agents must not read or write files outside their declared scope.

### 7.2 Tech stack context block (injected by Coordinator at dispatch)
```
## Technical Context (injected by Coordinator)
Stack: <contents of confirmed_stack.md>
Use only the tools and patterns appropriate for this stack.
Do not assume tools not listed here are available.
All Python dependencies must be installed inside a virtual environment (.venv).
```

### 7.3 Architect invocation modes
`agents/data_architect.md` is split into two invocation modes within the same file:

- **Mode A — Stack Proposal (Phase 1):** called with `intake.md` only. Output: `stack/stack_proposal.md`. Focus: evaluate requirements against approved open-source options, propose stack with trade-off rationale. Must not design data models in this mode.
- **Mode B — Model Design (Phase 2):** called with `intake.md` + `confirmed_stack.md`. Output: `design/data_contract.md` + `design/model_spec.md`. Focus: full medallion model design. Must not re-open stack decisions in this mode.

### 7.4 Engineer virtual environment requirement
`agents/data_engineer.md` adds a mandatory build output: every pipeline spec must include virtual environment setup steps. Mandatory files: `.venv` setup instructions, `requirements.txt` or `pyproject.toml`. Gate B will fail if these are absent.

---

## 8. Open-Source Constraint & Virtual Environment Standard

**New file: `standards/tech_constraints.md`**

Defines two policies:

### 8.1 Open-source-only policy
All tools in every stack must be open-source. Proprietary tools (Snowflake, BigQuery, Databricks, Power BI, Tableau, Looker, dbt Cloud features) are prohibited.

**Approved tool list:**

| Category | Approved |
|---|---|
| Transform | dbt (open-source), Apache Spark, Polars, Pandas |
| Storage | DuckDB, PostgreSQL, MySQL, MinIO, Apache Iceberg, Delta Lake |
| Orchestration | Apache Airflow, Dagster, Prefect, Mage |
| BI / Viz | Streamlit, Apache Superset, Metabase, Grafana |
| Data Quality | dbt tests, Great Expectations, Soda Core |
| Catalog / Lineage | OpenMetadata, DataHub, Amundsen |

Any tool not on this list requires explicit human approval before use.

### 8.2 Virtual environment requirement
Every Python-based project must:
- Create an isolated virtual environment: `python -m venv .venv` (or `uv venv`)
- Install all dependencies inside the venv — never globally
- Declare all dependencies in `requirements.txt` or `pyproject.toml`
- Document venv activation steps in the pipeline spec runbook

---

## 9. Gate Updates

**Gate A (Architect → Engineer) — additions:**
- Is every tool in the stack proposal on the approved open-source list?
- Is the confirmed stack consistent with the model design artifacts?

**Gate B (Engineer → BI) — additions:**
- Does the build output include venv setup instructions?
- Does a `requirements.txt` or `pyproject.toml` exist in the build spec?

All existing gate criteria are preserved.

---

## 10. File Change Summary

| File | Action |
|---|---|
| `CLAUDE.md` | New — entry point + slash command |
| `agents/coordinator.md` | Rewrite — phase-based orchestration workflow |
| `agents/data_architect.md` | Update — add File I/O, Mode A/B, tech context block |
| `agents/data_engineer.md` | Update — add File I/O, venv requirement, tech context block |
| `agents/data_bi.md` | Update — add File I/O, tech context block |
| `templates/intake.md` | Update — add volume, SLA, budget, infra, constraints fields |
| `standards/tech_constraints.md` | New — open-source policy + approved list + venv requirement |
| `gates/architect_to_engineer.md` | Update — add open-source compliance check |
| `gates/engineer_to_bi.md` | Update — add venv + dependency file check |
| `workspace/` | New directory — created empty, populated per request |

**Unchanged:**
- `team_operation.md`
- `standards/naming_conventions.md`
- `standards/layer_definitions.md`
- `standards/kpi_glossary.md`
- `standards/testing_policy.md`
- `standards/sla_freshness_policy.md`
- `gates/bi_to_coordinator.md`
- `templates/data_contract.md`
- `templates/model_spec.md`
- `templates/pipeline_spec.md`
- `templates/test_plan.md`
- `templates/dashboard_spec.md`
- `templates/release_checklist.md`

---

## 11. Definition of Done

This design is complete when:
- All files in the change summary above exist with correct content
- A `/data-request` command triggers the Coordinator intake workflow
- The Coordinator dispatches Architect (Mode A) → Engineer (stack) → human confirmation → Architect (Mode B) → Gate A → Engineer (build) → Gate B → BI → Gate C → sign-off
- Gate failures are always reported before any decision is made
- No agent dispatch uses a non-open-source tool
- Every build output includes venv setup and a dependency file
