-- silver_itbi_transactions.sql
-- Contract version: v1.0 (2026-05-01)
-- Materialization: table (full refresh)
-- Two logical sub-steps implemented as CTEs in a single model.

{{ config(materialized='table') }}

WITH

-- ===========================================================================
-- Sub-step 1: Typing, Parsing, and Cleaning
-- Source: bronze_itbi_transactions (all columns VARCHAR)
-- ===========================================================================
typed AS (
    SELECT
        -- Identity
        sql_cadastro,
        nome_logradouro,
        numero,
        complemento,
        bairro                                                      AS bairro_raw,
        referencia,
        cep,

        -- Transaction type parsing
        REGEXP_EXTRACT(natureza_transacao, '^([0-9]+)\.', 1)        AS natureza_transacao_codigo,
        REGEXP_REPLACE(natureza_transacao, '^[0-9]+\.\s*', '')      AS natureza_transacao_descricao,

        -- Core financials (TRY_CAST — NULL on parse failure)
        TRY_CAST(valor_transacao AS DECIMAL(18,2))                  AS valor_transacao,
        TRY_CAST(data_transacao AS DATE)                            AS data_transacao,

        -- Reference values (0 → NULL for reporting clarity)
        CASE
            WHEN TRY_CAST(valor_venal_referencia AS DECIMAL(18,2)) = 0 THEN NULL
            ELSE TRY_CAST(valor_venal_referencia AS DECIMAL(18,2))
        END                                                         AS valor_venal_referencia,

        TRY_CAST(proporcao_transmitida_pct AS DECIMAL(5,2))        AS proporcao_transmitida_pct,

        CASE
            WHEN TRY_CAST(valor_venal_proporcional AS DECIMAL(18,2)) = 0 THEN NULL
            ELSE TRY_CAST(valor_venal_proporcional AS DECIMAL(18,2))
        END                                                         AS valor_venal_proporcional,

        TRY_CAST(base_calculo AS DECIMAL(18,2))                    AS base_calculo,
        tipo_financiamento,
        TRY_CAST(valor_financiado AS DECIMAL(18,2))                AS valor_financiado,
        situacao_sql,

        -- Area fields
        TRY_CAST(area_terreno_m2 AS DECIMAL(12,2))                 AS area_terreno_m2,
        TRY_CAST(testada_m AS DECIMAL(10,2))                       AS testada_m,
        TRY_CAST(fracao_ideal AS DECIMAL(10,6))                    AS fracao_ideal,
        TRY_CAST(area_construida_m2 AS DECIMAL(12,2))              AS area_construida_m2,

        -- Use and standard codes (kept as VARCHAR for JOIN)
        uso_iptu_codigo                                             AS uso_codigo,
        uso_iptu_descricao,
        padrao_iptu_codigo                                          AS padrao_codigo,
        padrao_iptu_descricao,

        -- Year of construction
        TRY_CAST(acc_iptu AS INTEGER)                              AS acc_iptu,

        -- Metadata
        source_sheet,
        ingested_at

    FROM {{ ref('bronze_itbi_transactions') }}

    -- Filter: remove rows with no valid positive transaction value
    WHERE TRY_CAST(valor_transacao AS DECIMAL(18,2)) IS NOT NULL
      AND TRY_CAST(valor_transacao AS DECIMAL(18,2)) > 0
),

-- Derive month_year after typing (requires valid data_transacao)
typed_with_month AS (
    SELECT
        *,
        STRFTIME(data_transacao, '%Y-%m')                           AS month_year
    FROM typed
    WHERE data_transacao IS NOT NULL
),

-- ===========================================================================
-- Sub-step 2: Standardization, Enrichment, and Surrogate Key
-- ===========================================================================

-- 2a-i. Deduplicate CEP lookup: one canonical bairro per CEP
cep_lookup AS (
    SELECT cep, bairro AS bairro_from_cep
    FROM (
        SELECT
            cep,
            bairro,
            ROW_NUMBER() OVER (PARTITION BY cep ORDER BY bairro) AS rn
        FROM {{ ref('bronze_cep_lookup') }}
        WHERE bairro IS NOT NULL AND TRIM(bairro) != ''
    )
    WHERE rn = 1
),

-- 2a-ii. Enrich with CEP-derived bairro where source bairro is NULL
cep_enriched AS (
    SELECT
        t.*,
        cl.bairro_from_cep
    FROM typed_with_month t
    LEFT JOIN cep_lookup cl
        ON LPAD(REGEXP_REPLACE(COALESCE(t.cep, ''), '[^0-9]', ''), 8, '0') = cl.cep
),

-- 2b. Neighborhood normalization via macro; uses CEP fallback, then 'DESCONHECIDO'
normalized AS (
    SELECT
        *,
        COALESCE(
            NULLIF(TRIM(
                {{ normalize_bairro('COALESCE(bairro_raw, bairro_from_cep)') }}
            ), ''),
            'DESCONHECIDO'
        )                                                           AS bairro_normalized
    FROM cep_enriched
),

-- 2b. Use code resolution (LEFT JOIN — unresolved codes fall back to source description)
uso_resolved AS (
    SELECT
        n.*,
        COALESCE(u.uso_descricao_canonical, n.uso_iptu_descricao)   AS uso_desc,
        u.uso_categoria
    FROM normalized n
    LEFT JOIN {{ ref('seed_uso_lookup') }} u
        ON n.uso_codigo = u.uso_codigo
),

-- 2c. Construction standard code resolution
padrao_resolved AS (
    SELECT
        u.*,
        COALESCE(p.padrao_descricao_canonical, u.padrao_iptu_descricao) AS padrao_desc,
        p.padrao_categoria
    FROM uso_resolved u
    LEFT JOIN {{ ref('seed_padrao_lookup') }} p
        ON u.padrao_codigo = p.padrao_codigo
),

-- 2d. Derived price_per_m2 (null-safe) + surrogate transaction_id
enriched AS (
    SELECT
        -- Surrogate key (deterministic, idempotent across re-runs)
        md5(
            COALESCE(sql_cadastro, '') || '|' ||
            CAST(data_transacao AS VARCHAR) || '|' ||
            CAST(valor_transacao AS VARCHAR) || '|' ||
            COALESCE(source_sheet, '')
        )                                                           AS transaction_id,

        -- Core identity
        sql_cadastro,
        nome_logradouro,
        numero,
        complemento,
        bairro_raw,
        bairro_from_cep,
        bairro_normalized,
        referencia,
        cep,

        -- Transaction type
        natureza_transacao_codigo,
        natureza_transacao_descricao,

        -- Financials
        valor_transacao,
        data_transacao,
        month_year,
        valor_venal_referencia,
        proporcao_transmitida_pct,
        valor_venal_proporcional,
        base_calculo,
        tipo_financiamento,
        valor_financiado,

        -- Property attributes
        situacao_sql,
        area_terreno_m2,
        testada_m,
        fracao_ideal,
        area_construida_m2,

        -- Use type (resolved)
        uso_codigo,
        uso_desc,
        uso_categoria,

        -- Construction standard (resolved)
        padrao_codigo,
        padrao_desc,
        padrao_categoria,

        -- Year of construction
        acc_iptu,

        -- Derived KPI
        CASE
            WHEN area_construida_m2 IS NULL OR area_construida_m2 = 0 THEN NULL
            ELSE ROUND(valor_transacao / area_construida_m2, 2)
        END                                                         AS price_per_m2,

        -- Lineage metadata
        source_sheet,
        ingested_at,
        CURRENT_TIMESTAMP                                           AS created_at

    FROM padrao_resolved
)

SELECT * FROM enriched
