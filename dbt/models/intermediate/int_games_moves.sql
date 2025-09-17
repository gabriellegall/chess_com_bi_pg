{{ config(
    materialized = 'incremental',
    unique_key = ['uuid','move_number'],
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)"
    ]
) }}

SELECT 
    pgm.*,
    CASE WHEN MOD(move_number, 2) = 1 THEN 'White' ELSE 'Black' END AS player_color_turn,
    -score_white                                                    AS score_black,
    1.0 / (1 + EXP(-0.004 * score_white))                           AS win_probability_white,
    1.0 - 1.0 / (1 + EXP(-0.004 * score_white))                     AS win_probability_black
FROM {{ source('stockfish', 'players_games_moves') }} pgm

{% if is_incremental() %}
WHERE NOT EXISTS (
    SELECT 1
    FROM {{ this }} i
    WHERE i.uuid = pgm.uuid
)
{% endif %}