-- gold_itbi_monthly_summary.sql
-- Contract version: v1.0 (2026-05-01)
-- Grain: one row per calendar month (YYYY-MM)
-- Feeds: Chart 1 — Month-over-month price evolution

{{ config(materialized='table') }}

SELECT
    md5(month_year)                                                  AS monthly_summary_id,
    month_year,
    COUNT(*)                                                         AS transaction_count,
    SUM(valor_transacao)                                             AS total_value_brl,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY valor_transacao)     AS kpi_median_price,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_per_m2)
        FILTER (WHERE price_per_m2 IS NOT NULL)                      AS kpi_median_price_per_m2,
    AVG(price_per_m2) FILTER (WHERE price_per_m2 IS NOT NULL)        AS avg_price_per_m2,
    CURRENT_TIMESTAMP                                                AS created_at

FROM {{ ref('silver_itbi_transactions') }}
GROUP BY month_year
ORDER BY month_year
