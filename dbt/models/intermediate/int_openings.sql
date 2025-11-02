{{ config(
    materialized = 'view'
) }}

-- Dynamically determine the maximum depth of UCI move sequences in the source data using [uci_moves_depth]
{% set get_max_depth_query %}
    SELECT
        MAX(ARRAY_LENGTH(REGEXP_SPLIT_TO_ARRAY(UCI, ' '), 1)) AS uci_moves_depth
    FROM {{ source('openings', 'chess_openings') }}
{% endset %}

{% set max_depth_results = run_query(get_max_depth_query) %}
{% if execute %}
    {% set max_depth = max_depth_results.columns[0].values()[0] %}
{% else %}
    {% set max_depth = 10 %} {# default value for the DBT project parse phase (https://docs.getdbt.com/reference/dbt-jinja-functions/execute) #}
{% endif %}

WITH extract_moves AS (
    SELECT
        *,
        REGEXP_SPLIT_TO_ARRAY(UCI, ' ')                         AS uci_moves_array,
        ARRAY_LENGTH(REGEXP_SPLIT_TO_ARRAY(UCI, ' '), 1)        AS uci_moves_depth
    FROM {{ source('openings', 'chess_openings') }}
),

-- Generate [uci] keys for previous hierarchy levels only
parent_hierarchy AS (
    SELECT
        *,
        {% for i in range(1, max_depth) %}
            CASE 
                WHEN {{ i }} <= uci_moves_depth THEN ARRAY_TO_STRING(UCI_MOVES_ARRAY[1:{{ i }}], ' ')
            END AS uci_hierarchy_level_{{ i }}{% if not loop.last %},{% endif %}
        {% endfor %}
    FROM extract_moves
)

-- For each previous hierarchy level, join to the original table to get the [name] (if any matches!)
, parent_hierarchy_with_names AS (
    SELECT
        p.*,
        {% for i in range(1, max_depth) %}
            level_{{ i }}.name AS uci_hierarchy_level_{{ i }}_name_matching{% if not loop.last %},{% endif %}
        {% endfor %}
    FROM parent_hierarchy p
    {% for i in range(1, max_depth) %}
        LEFT JOIN {{ source('openings', 'chess_openings') }} AS level_{{ i }}
        ON level_{{ i }}.UCI = p.uci_hierarchy_level_{{ i }}
    {% endfor %}
)

, parent_hierarchy_with_filled_names AS (
    SELECT
        eco,
        "eco-volume",
        name,
        pgn,
        epd,
        log_timestamp,
        uci,
        uci_moves_array,
        uci_moves_depth,
        {% for i in range(1, max_depth) %}
            {% if i == 1 %}
                uci_hierarchy_level_1_name_matching AS uci_hierarchy_level_1_name
            {% else %}
                COALESCE(
                    -- Search for the first non-null name_matching from the current level up to level 1
                    uci_hierarchy_level_{{ i }}_name_matching,
                    {% for j in range(i-1, 0, -1) %}
                        uci_hierarchy_level_{{ j }}_name_matching{% if not loop.last %}, {% endif %}
                    {% endfor %}
                ) AS uci_hierarchy_level_{{ i }}_name
            {% endif %}
            {% if not loop.last %},{% endif %}
        {% endfor %}
    FROM parent_hierarchy_with_names
)

SELECT
    *
FROM parent_hierarchy_with_filled_names
ORDER BY uci