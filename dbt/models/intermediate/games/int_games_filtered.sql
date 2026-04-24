{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_end_time ON {{ this }} (end_time)"
    ]
) }}

select
    g.*
from {{ ref('int_games_base') }} g
where true
    and {{ games_scope_condition('g') }}
    {% if is_incremental() %}
    and not exists (
        select 1
        from {{ this }} i
        where i.uuid = g.uuid
    )
    {% endif %}