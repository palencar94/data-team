# ITBI SP — Known Data Quality Issues

This document captures all known data quality issues, their root causes, severity, and how they are handled. Do not re-raise these as blocking failures — they are documented, understood, and intentionally handled.

---

## DQ-001: NULL bairro in source (~41% of rows)

**Severity:** WARN (not fail)
**Scope:** `raw_itbi_transactions.bairro` — 20,179 of 49,164 rows
**Root cause:** The source XLSX has many transactions where the neighborhood field is blank. This is common in ITBI data where the cadastre system does not always record the bairro.
**Resolution:** CEP enrichment in Silver. The `cep_enriched` CTE joins `bronze_cep_lookup` on LPAD(cep, 8, '0') and provides `bairro_from_cep`. After enrichment, only 14 rows remain as `DESCONHECIDO` (0.03%).
**dbt test:** `not_null_silver_itbi_transactions_bairro_raw` — severity: warn
**Soda check:** `bairro_not_null` — warn when > 0

---

## DQ-002: Duplicate composite keys (~1,161 rows)

**Severity:** WARN (not fail)
**Scope:** `silver_itbi_transactions.transaction_id` — 1,161 non-unique values
**Root cause:** The MD5 surrogate key is derived from `(sql_cadastro, data_transacao, valor_transacao, source_sheet)`. Some legitimate transactions share all four values (e.g., split-lot sales registered on the same day at the same price).
**Resolution:** Accepted as warn. The transaction_id is still useful for approximate deduplication. If exact uniqueness is needed in the future, an additional column (sequence number or index) from the source would be required.
**dbt test:** `unique_silver_itbi_transactions_transaction_id` — severity: warn

---

## DQ-003: 126 unresolved uso_codigo values

**Severity:** WARN (not fail)
**Scope:** `silver_itbi_transactions.uso_codigo` — 126 rows reference codes not present in `seed_uso_lookup`
**Root cause:** The seed was extracted from the data dictionary sheet which may not cover all codes present in the transactions.
**Resolution:** `COALESCE(u.uso_descricao_canonical, n.uso_iptu_descricao)` falls back to the source description. These rows still appear in Gold with the raw description as `uso_desc`.
**dbt test:** `relationships_silver_itbi_transactions_uso_codigo` — severity: warn

---

## DQ-004: proporcao_transmitida_pct > 100 (4 rows)

**Severity:** WARN (not fail)
**Scope:** `silver_itbi_transactions.proporcao_transmitida_pct` — 4 rows with values like 141.71, 309.87
**Root cause:** In São Paulo ITBI law, partial interest transfers can accumulate percentages exceeding 100% (e.g., multiple co-owners each transferring their share). This is legally valid.
**Resolution:** The `BETWEEN 0 AND 100` test is set to severity: warn. Values are kept as-is.
**dbt test:** `dbt_utils.expression_is_true` on proporcao_transmitida_pct — severity: warn

---

## DQ-005: price_per_m2 = 0 (89 rows in silver, 22 in gold)

**Severity:** WARN (not fail)
**Scope:** Silver and Gold tables
**Root cause:** Some transactions have very small `valor_transacao` (e.g., R$0.01) but a large area. `ROUND(0.01 / 50.0, 2) = 0.00`. The value rounds to zero but is not NULL.
**Resolution:** The `> 0 OR price_per_m2 IS NULL` test is set to severity: warn. These rows have negligible business impact as they represent token-value transactions.
**dbt test:** severity: warn

---

## DQ-006: FEV-2026 sheet missing padrao_iptu_descricao column

**Severity:** INFO (no test, no action needed)
**Scope:** FEV-2026 sheet only
**Root cause:** The February 2026 source sheet omits the `Descrição do padrão (IPTU)` column entirely. The ingestion script handles this gracefully (missing mapped columns → NULL in DuckDB).
**Resolution:** `padrao_iptu_descricao` is NULL for all FEV-2026 rows. The `padrao_desc` column in Silver falls back to `NULL` (no canonical description) for these rows.

---

## DQ-007: MoM price change outside ±100–500% range (203 rows)

**Severity:** WARN (not fail)
**Scope:** `gold_itbi_neighborhood_ranking.kpi_mom_price_change_pct`
**Root cause:** Some neighborhoods have very few transactions (1-2 per month). A single large transaction can produce extreme MoM swings. This is a statistical artifact of low-volume neighborhoods, not a data error.
**Resolution:** The test allows values `BETWEEN -100 AND 500 OR IS NULL` — severity: warn. Dashboard consumers should apply a minimum transaction count filter when interpreting MoM metrics.
**dbt test:** severity: warn (with 500% upper bound to catch egregious outliers)

---

## Soda Exit Code Behavior

Soda Core exits:
- Code 0 — all checks pass
- Code 1 — at least one WARNING (pipeline continues)
- Code 2+ — at least one FAILURE (pipeline stops)

The Makefile `soda-bronze` target is coded as: `if [ $EXIT -gt 1 ]; then exit $EXIT; fi` — warnings pass through.
