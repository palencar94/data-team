-- gold_itbi_price_per_m2.sql
-- Contract version: v1.0 (2026-05-01)
-- Grain: one row per (bairro_normalized, uso_desc, month_year)
-- Only rows where price_per_m2 IS NOT NULL (area_construida_m2 > 0)
-- Feeds: Chart 3 — Price per m² trend by neighborhood and use type

{{ config(materialized='table') }}

SELECT
    md5(
        bairro_normalized || '|' ||
        COALESCE(uso_desc, 'UNKNOWN') || '|' ||
        month_year
    )                                                                  AS price_m2_id,
    bairro_normalized,
    COALESCE(uso_desc, 'UNKNOWN')                                      AS uso_desc,
    month_year,
    COUNT(*)                                                           AS transaction_count,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_per_m2)         AS kpi_median_price_per_m2,
    AVG(price_per_m2)                                                  AS kpi_avg_price_per_m2,
    CURRENT_TIMESTAMP                                                  AS created_at

FROM {{ ref('silver_itbi_transactions') }}
WHERE price_per_m2 IS NOT NULL

GROUP BY bairro_normalized, COALESCE(uso_desc, 'UNKNOWN'), month_year
