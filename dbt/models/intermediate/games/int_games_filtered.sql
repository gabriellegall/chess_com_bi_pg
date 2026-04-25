{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_end_time ON {{ this }} (end_time)"
    ]
) }}

select
    g.*
from {{ ref('int_games_base') }} g
where true
    and {{ games_scope_condition('g') }}
    {% if is_incremental() %}
    and g.end_time > (
        select max(i.end_time)
        from {{ this }} i
    )
    {% endif %}