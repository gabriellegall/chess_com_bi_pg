{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

{% set openings_depth = var('openings')['hierarchy_depth'] + 1 %}

WITH aggregate_fields AS (
    SELECT
        games.username,
        games.uuid,
        max(games.log_timestamp) AS log_timestamp,
        {% for n in range(1, openings_depth) %}
            string_agg(CASE WHEN games.move_number <= {{ n }} THEN games.move ELSE NULL END, ' ' ORDER BY games.move_number ASC) AS opener_{{ n }}_moves{% if not loop.last %},{% endif %}
        {% endfor %}
    FROM {{ ref('int_game_moves_enriched') }} games
    {% if is_incremental() %}
        WHERE games.log_timestamp > (
            SELECT max(i.log_timestamp)
            FROM {{ this }} i
        )
    {% endif %}
    GROUP BY games.username, games.uuid
)

, integrate_openings_hierarchy AS (
    SELECT
        agg.*,
        {% for i in range(1, openings_depth, 1) %}
            coalesce(
                {% for j in range(openings_depth - 1, 0, -1) %}
                    op{{ j }}.uci_hierarchy_level_{{ i }}_name{% if not loop.last %},{% endif %}
                {% endfor %}
            ) AS uci_hierarchy_level_{{ i }}_name{% if not loop.last %},{% endif %}
        {% endfor %}
    FROM aggregate_fields agg
    {% for i in range(1, openings_depth, 1) %}
        LEFT JOIN {{ ref('int_openings_hierarchy') }} op{{ i }}
            ON agg.opener_{{ i }}_moves = op{{ i }}.uci
    {% endfor %}
)

SELECT
    *
FROM integrate_openings_hierarchy