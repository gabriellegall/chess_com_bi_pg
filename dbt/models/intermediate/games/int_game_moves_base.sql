{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid, move_number)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

select 
    pgm.*
from {{ ref('stg_stockfish__players_games_moves') }} pgm
{% if is_incremental() %}
where pgm.log_timestamp > (
    select max(i.log_timestamp)
    from {{ this }} i
)
{% endif %}