# ITBI SP — Technical Decisions

Decisions made during implementation, rationale, and implications for future changes.

---

## TD-001: DuckDB single-writer constraint

**Decision:** DuckDB is used as the sole storage engine.
**Implication:** DuckDB allows only one writer at a time. When Streamlit holds the database open (read mode), Python ingestion scripts and dbt runs will fail with a lock error.
**Workaround:** Always stop Streamlit before running `make pipeline`. Restart after.
**Future option:** If concurrent access becomes a requirement, migrate to PostgreSQL (on approved stack list) which supports multi-writer access.

---

## TD-002: CEP LPAD normalization

**Decision:** ITBI source CEPs are stored as 7-digit strings (Excel strips the leading zero). The `cep_sp.csv` lookup uses 8-digit strings.
**Fix applied:** Silver model uses `LPAD(REGEXP_REPLACE(COALESCE(cep, ''), '[^0-9]', ''), 8, '0')` on the ITBI side before joining.
**Result:** 20,165 of 20,179 NULL bairros filled by CEP lookup.
**Never strip dashes and forget to pad** — REGEXP_REPLACE alone was tried first and produced 0 matches.

---

## TD-003: Bronze table renamed to avoid circular reference

**Decision:** The raw DuckDB table is named `raw_itbi_transactions`, NOT `bronze_itbi_transactions`.
**Reason:** The dbt Bronze model is named `bronze_itbi_transactions` and does `SELECT * FROM raw_itbi_transactions`. If the raw table were also named `bronze_itbi_transactions`, DuckDB would detect an infinite recursion when resolving the view.
**Rule:** Raw tables (populated by Python scripts) are always prefixed `raw_`. Bronze dbt views are prefixed `bronze_`.

---

## TD-004: Soda check exit code handling

**Decision:** The Makefile `soda-bronze` target does not treat exit code 1 as a failure.
**Reason:** Soda Core exits 1 for warnings, 2 for failures. Many source data warnings are expected (see DQ-001 through DQ-007) and should not block the pipeline.
**Pattern:** `EXIT=$$?; if [ $$EXIT -gt 1 ]; then exit $$EXIT; fi`

---

## TD-005: dbt-utils expression_is_true format

**Decision:** Column-level `expression_is_true` tests must NOT include the column name in the expression string.
**Reason:** dbt-utils prepends the column name automatically when the test is defined at column level. Writing `expression: "valor_transacao > 0"` on column `valor_transacao` generates `WHERE NOT (valor_transacao valor_transacao > 0)` — invalid SQL.
**Correct format:**
```yaml
- name: valor_transacao
  tests:
    - dbt_utils.expression_is_true:
        expression: "> 0"
```
For expressions with secondary column references: `expression: ">= 0 OR area_construida_m2 IS NULL"` (column name only on the second reference, which is literal text in the expression).

---

## TD-006: Python 3.9 compatibility

**Decision:** No `str | None` union type hints (Python 3.10+ syntax).
**Reason:** The environment runs Python 3.9 where `X | Y` type unions in annotations are not supported.
**Pattern:** Use `Optional[str]` from `typing` or omit the return type annotation entirely.

---

## TD-007: normalize_bairro macro paren discipline

**Decision:** The `normalize_bairro` macro stacks 31 REPLACE() calls inside UPPER() inside TRIM(REGEXP_REPLACE()) inside 14 outer REGEXP_REPLACE() calls.
**Critical rule:** The number of REPLACE( opens must exactly equal the number of replacement patterns (31). The TRIM(REGEXP_REPLACE() inner call must NOT have a `)` before the `, '\s+', ' ')` arguments — UPPER() already provides its own closing `)`.
**Past bug:** Line 35 had `), '\s+', ' '))` instead of `, '\s+', ' '))`. Also, 29 opens were used instead of 31 (the fifth row of REPLACE( calls had 5 instead of 7).

---

## TD-008: seed column type coercion

**Decision:** `seed_uso_lookup.uso_codigo` and `seed_padrao_lookup.padrao_codigo` are forced to `varchar` in `dbt_project.yml`.
**Reason:** Without this, DuckDB infers numeric types from values like `01`, `02`, which causes `JOIN ... ON uso_codigo = u.uso_codigo` to fail when the Silver side has `'01'` (string) and the seed has `1` (integer).
**Config:**
```yaml
seeds:
  itbi_sp:
    seed_uso_lookup:
      +column_types:
        uso_codigo: varchar
```

---

## TD-009: CEP lookup full-refresh strategy

**Decision:** `scripts/load_cep_lookup.py` drops and recreates `raw_cep_lookup` on every run.
**Reason:** The CSV is a static reference file. A full refresh is simpler and faster than an incremental merge for a 300K-row lookup table.
**Implication:** If the CSV changes, the entire table is replaced atomically.
