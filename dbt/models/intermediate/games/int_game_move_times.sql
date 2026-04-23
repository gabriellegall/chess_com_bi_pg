{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid, move_number)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

select
    pgt.*
from {{ ref('stg_times__players_games_times') }} pgt
{% if is_incremental() %}
where pgt.log_timestamp > (
    select max(i.log_timestamp)
    from {{ this }} i
)
{% endif %}