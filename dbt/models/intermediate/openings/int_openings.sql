{{ config(
    materialized = 'table'
) }}

-- Dynamically determine the maximum depth of UCI move sequences in the source data using [uci_moves_depth]
{% set get_max_depth_query %}
    select
        max(array_length(regexp_split_to_array(uci, ' '), 1)) as uci_moves_depth
    from {{ source('openings', 'chess_openings') }}
{% endset %}

{% set max_depth_results = run_query(get_max_depth_query) %}
{% if execute %}
    {% set max_depth = max_depth_results.columns[0].values()[0] %}
{% else %}
    {% set max_depth = 10 %} {# dummy default value for the DBT project parse phase (https://docs.getdbt.com/reference/dbt-jinja-functions/execute) #}
{% endif %}

with extract_moves as (
    select
        *,
        regexp_split_to_array(uci, ' ')                         as uci_moves_array,
        array_length(regexp_split_to_array(uci, ' '), 1)        as uci_moves_depth
    from {{ ref('stg_openings__chess_openings') }}
),

-- Generate [uci] keys for previous hierarchy levels only
parent_hierarchy as (
    select
        *,
        {% for i in range(1, max_depth) %}
            case 
                when {{ i }} <= uci_moves_depth then array_to_string(uci_moves_array[1:{{ i }}], ' ')
            end as uci_hierarchy_level_{{ i }}{% if not loop.last %},{% endif %}
        {% endfor %}
    from extract_moves
)

-- For each previous hierarchy level, join to the original table to get the [name] (if any matches!)
, parent_hierarchy_with_names as (
    select
        p.*,
        {% for i in range(1, max_depth) %}
            level_{{ i }}.name as uci_hierarchy_level_{{ i }}_name_matching{% if not loop.last %},{% endif %}
        {% endfor %}
    from parent_hierarchy p
    {% for i in range(1, max_depth) %}
        left join {{ ref('stg_openings__chess_openings') }} as level_{{ i }}
        on level_{{ i }}.UCI = p.uci_hierarchy_level_{{ i }}
    {% endfor %}
)

, parent_hierarchy_with_filled_names as (
    select
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
                uci_hierarchy_level_1_name_matching as uci_hierarchy_level_1_name
            {% else %}
                coalesce(
                    -- To fill the blank [name], search for the first non-null name_matching from the current level up to level 1
                    uci_hierarchy_level_{{ i }}_name_matching,
                    {% for j in range(i-1, 0, -1) %}
                        uci_hierarchy_level_{{ j }}_name_matching{% if not loop.last %}, {% endif %}
                    {% endfor %}
                ) as uci_hierarchy_level_{{ i }}_name
            {% endif %}
            {% if not loop.last %},{% endif %}
        {% endfor %}
    from parent_hierarchy_with_names
)

select
    *
from parent_hierarchy_with_filled_names
order by uci