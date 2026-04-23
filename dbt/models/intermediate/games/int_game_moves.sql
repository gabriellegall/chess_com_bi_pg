{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid, move_number)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

select 
    pgm.*,
    case when mod(move_number, 2) = 1 then 'White' else 'Black' end as player_color_turn,
    -score_white                                                    as score_black,
    1.0 / (1 + exp(-0.004 * score_white))                           as win_probability_white,
    1.0 - 1.0 / (1 + exp(-0.004 * score_white))                     as win_probability_black
from {{ ref('stg_stockfish__players_games_moves') }} pgm
{% if is_incremental() %}
where pgm.log_timestamp > (
    select max(i.log_timestamp)
    from {{ this }} i
)
{% endif %}