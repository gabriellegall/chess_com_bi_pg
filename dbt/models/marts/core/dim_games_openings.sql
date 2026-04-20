{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

{# This variable controls the maximum number of moves that are used to match and integrate the openings hierarchy #}
{% set openings_depth = var('openings')['hierarchy_depth'] + 1 %}  {# use '+1' includes the outer bond for use in the Jinja loop #}

WITH aggregate_fields AS (
    SELECT 
        username,
        uuid,
        MAX(log_timestamp) AS log_timestamp,
        -- Opening Moves
        {% for n in range(1, openings_depth) %}
            STRING_AGG(CASE WHEN move_number <= {{ n }} THEN move ELSE NULL END, ' ' ORDER BY move_number ASC)                          AS opener_{{ n }}_moves
            {% if not loop.last %},{% endif %}
        {% endfor %}
    FROM {{ ref('fct_games_with_moves') }} games
    {% if is_incremental() %}
    WHERE games.log_timestamp > (
        SELECT MAX(i.log_timestamp)
        FROM {{ this }} i
    )
    {% endif %}
    GROUP BY username, uuid
)

, integrate_openings_hierarchy AS (
    SELECT 
        agg.*,
        {% for i in range(1, openings_depth, 1) %}
        -- Among all matched openings, select the most specific opening hierarchy available
            COALESCE(
                {% for j in range(openings_depth - 1, 0, -1) %} -- Deepest to shallowest - i.e. prioritize the most specific opening hierarchy
                    op{{ j }}.uci_hierarchy_level_{{ i }}_name{% if not loop.last %},{% endif %}
                {% endfor %}
                ) AS uci_hierarchy_level_{{ i }}_name
                {% if not loop.last %},{% endif %}
        {% endfor %}
    FROM aggregate_fields agg
    {% for i in range(1, openings_depth, 1) %}
    -- Attempt to match on each and every opening moves
    LEFT OUTER JOIN {{ ref('int_openings') }} op{{ i }}
        ON agg.opener_{{ i }}_moves = op{{ i }}.uci
    {% endfor %}
)

SELECT 
    *
FROM integrate_openings_hierarchy
