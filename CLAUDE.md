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
2. Never dispatch a subagent for a phase without first writing all artifacts produced in the preceding phase to the workspace.
3. Always report gate results (PASS or FAIL with specific reasons) before taking any action on them.
4. `workspace/<request-id>/` is the only shared state between agents — never pass artifacts through conversation context alone.
5. All tools in every recommended stack must be open-source. See `standards/tech_constraints.md`.
6. All Python projects must use a virtual environment. See `standards/tech_constraints.md`.
