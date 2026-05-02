-- bronze_itbi_transactions.sql
-- Passthrough view over the DuckDB table populated by scripts/ingest.py
-- Contract version: v1.0 (2026-05-01)

{{ config(materialized='view') }}

SELECT * FROM raw_itbi_transactions
