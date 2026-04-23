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
    and g.end_time >= date_trunc('month', current_date - interval '{{ var('data_scope')['month_history_depth'] }} months')
    and g.time_class = any(array{{ var('data_scope')['time_class'] }}::text[])
    and g.rated
    {% if is_incremental() %}
    and not exists (
        select 1
        from {{ this }} i
        where i.uuid = g.uuid
    )
    {% endif %}