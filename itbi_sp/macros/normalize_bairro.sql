{% macro normalize_bairro(col) %}
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    TRIM(REGEXP_REPLACE(
    UPPER(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            {{ col }},
        'ã','a'),'â','a'),'à','a'),'á','a'),'ä','a'),
        'ê','e'),'é','e'),'è','e'),'ë','e'),
        'í','i'),'ì','i'),'ï','i'),
        'õ','o'),'ô','o'),'ó','o'),'ò','o'),'ö','o'),
        'ú','u'),'ù','u'),'ü','u'),
        'ç','c'),
        'Ã','A'),'Â','A'),'Á','A'),'À','A'),
        'Ê','E'),'É','E'),
        'Í','I'),
        'Õ','O'),'Ô','O'),'Ó','O')
    )
    , '\s+', ' '))
    , '\bCJTO\b', 'CONJUNTO')
    , '\bCONJ\b', 'CONJUNTO')
    , '\bNCL\b', 'NUCLEO')
    , '\bST\b', 'SETOR')
    , '\bLT\b', 'LOTEAMENTO')
    , '\bCHAC\b', 'CHACARA')
    , '\bCH\b', 'CHACARA')
    , '\bPQE\b', 'PARQUE')
    , '\bPQ\b', 'PARQUE')
    , '\bJARD\b', 'JARDIM')
    , '\bJD\b', 'JARDIM')
    , '\bVL\b', 'VILA')
    , '\bV\b', 'VILA')
    , '\bJARDIM\b', 'JARDIM')
{% endmacro %}
