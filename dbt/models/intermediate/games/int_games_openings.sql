{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

{% set openings_depth = var('openings')['hierarchy_depth'] + 1 %}

with aggregate_fields as (
    select
        username,
        uuid,
        max(log_timestamp) as log_timestamp,
        {% for n in range(1, openings_depth) %}
            string_agg(case when move_number <= {{ n }} then move else null end, ' ' order by move_number asc) as opener_{{ n }}_moves{% if not loop.last %},{% endif %}
        {% endfor %}
    from {{ ref('int_game_moves_enriched') }} games
    {% if is_incremental() %}
    where games.log_timestamp > (
        select max(i.log_timestamp)
        from {{ this }} i
    )
    {% endif %}
    group by username, uuid
)

, integrate_openings_hierarchy as (
    select
        agg.*,
        {% for i in range(1, openings_depth, 1) %}
            coalesce(
                {% for j in range(openings_depth - 1, 0, -1) %}
                    op{{ j }}.uci_hierarchy_level_{{ i }}_name{% if not loop.last %},{% endif %}
                {% endfor %}
            ) as uci_hierarchy_level_{{ i }}_name{% if not loop.last %},{% endif %}
        {% endfor %}
    from aggregate_fields agg
    {% for i in range(1, openings_depth, 1) %}
    left join {{ ref('int_openings_hierarchy') }} op{{ i }}
        on agg.opener_{{ i }}_moves = op{{ i }}.uci
    {% endfor %}
)

select
    *
from integrate_openings_hierarchy