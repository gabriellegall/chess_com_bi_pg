{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

SELECT 
    pgm.uuid,
    pgm.move_number,
    pgm.move,
    pgm.score_white,
    pgm.log_timestamp,
    pgm.player_color_turn,
    pgm.score_black,
    pgm.win_probability_white,
    pgm.win_probability_black
FROM {{ ref('stg_stockfish__players_games_moves') }} pgm
{% if is_incremental() %}
WHERE pgm.log_timestamp > (
    SELECT max(i.log_timestamp)
    FROM {{ this }} i
)
{% endif %}