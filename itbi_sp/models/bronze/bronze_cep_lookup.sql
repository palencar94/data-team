{{ config(materialized='view') }}

SELECT * FROM raw_cep_lookup
