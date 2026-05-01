# Gate: Engineer -> BI

## Pass Criteria

### Build Outputs
- [ ] Gold datasets available and documented
- [ ] Mandatory tests passed
- [ ] Freshness checks pass or approved exception exists
- [ ] Join guidance for BI included in `build/bi_handoff.md`
- [ ] Known caveats documented

### Virtual Environment Compliance (mandatory — auto-FAIL if any item fails)
- [ ] `build/pipeline_spec.md` includes the venv creation command (`python -m venv .venv` or `uv venv`)
- [ ] `build/pipeline_spec.md` includes the activation command for at least Linux/macOS (`source .venv/bin/activate`)
- [ ] `build/pipeline_spec.md` includes full contents of `requirements.txt` or `pyproject.toml`
- [ ] `build/pipeline_spec.md` includes a confirmation statement that all dependencies are installed inside the venv (not globally)
- [ ] `build/pipeline_spec.md` contains no `sudo pip install`, `pip install --user`, or bare `pip install` commands appearing before the venv activation step

### Stack Compliance
- [ ] `stack/confirmed_stack.md` exists and is non-empty (pre-condition — if absent, escalate immediately)
- [ ] No tool referenced in `build/pipeline_spec.md`, `build/test_plan.md`, or `build/bi_handoff.md` is absent from `stack/confirmed_stack.md`

## Fail Conditions
- Failing critical tests
- No gold documentation
- Missing caveat disclosure
- Missing venv creation command in pipeline spec
- Missing venv activation command in pipeline spec
- Missing requirements.txt or pyproject.toml contents in pipeline spec
- Missing confirmation that all deps are inside the venv
- Any `sudo pip install`, `pip install --user`, or pre-activation `pip install` found in pipeline spec
- Build artifacts reference a tool not in confirmed_stack.md
- A proprietary tool appears in any build artifact
