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