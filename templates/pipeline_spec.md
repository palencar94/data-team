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

## Virtual Environment Setup
> Required for all Python-based projects. See standards/tech_constraints.md.
- venv creation command:
- Activation command (Linux/macOS):
- Activation command (Windows):
- Dependency file (`requirements.txt` or `pyproject.toml`):

```
<paste full requirements.txt or pyproject.toml contents here>
```

- Confirmation: all dependencies installed inside venv (not globally):

## Operational Runbook
- How to rerun:
- Backfill approach:
- Common failure modes: