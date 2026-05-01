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
