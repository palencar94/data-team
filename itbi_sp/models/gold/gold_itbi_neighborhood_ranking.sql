-- gold_itbi_neighborhood_ranking.sql
-- Contract version: v1.0 (2026-05-01)
-- Grain: one row per (bairro_normalized, month_year)
-- Feeds: Chart 2 — Neighborhood ranking + MoM appreciation

{{ config(materialized='table') }}

WITH base AS (
    SELECT
        bairro_normalized,
        month_year,
        COUNT(*)                                                              AS transaction_count,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY valor_transacao)         AS kpi_median_price,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_per_m2)
            FILTER (WHERE price_per_m2 IS NOT NULL)                          AS kpi_median_price_per_m2
    FROM {{ ref('silver_itbi_transactions') }}
    GROUP BY bairro_normalized, month_year
),

with_mom AS (
    SELECT
        *,
        LAG(kpi_median_price)
            OVER (PARTITION BY bairro_normalized ORDER BY month_year)        AS prev_median_price,
        LAG(kpi_median_price_per_m2)
            OVER (PARTITION BY bairro_normalized ORDER BY month_year)        AS prev_median_price_per_m2
    FROM base
)

SELECT
    md5(bairro_normalized || '|' || month_year)                       AS neighborhood_month_id,
    bairro_normalized,
    month_year,
    transaction_count,
    kpi_median_price,
    kpi_median_price_per_m2,
    CASE
        WHEN prev_median_price IS NULL OR prev_median_price = 0 THEN NULL
        ELSE ROUND(((kpi_median_price - prev_median_price) / prev_median_price) * 100, 4)
    END                                                               AS kpi_mom_price_change_pct,
    CASE
        WHEN prev_median_price_per_m2 IS NULL OR prev_median_price_per_m2 = 0 THEN NULL
        ELSE ROUND(((kpi_median_price_per_m2 - prev_median_price_per_m2) / prev_median_price_per_m2) * 100, 4)
    END                                                               AS kpi_mom_price_per_m2_change_pct,
    CURRENT_TIMESTAMP                                                 AS created_at

FROM with_mom
