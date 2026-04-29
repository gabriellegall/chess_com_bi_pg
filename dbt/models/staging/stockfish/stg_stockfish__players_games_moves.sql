{{ config(materialized = 'view') }}

SELECT
    pgm.*,
    CASE WHEN MOD(pgm.move_number, 2) = 1 THEN 'White' ELSE 'Black' END AS player_color_turn,
    -pgm.score_white AS score_black,
    1.0 / (1 + EXP(-0.004 * pgm.score_white)) AS win_probability_white,
    1.0 - 1.0 / (1 + EXP(-0.004 * pgm.score_white)) AS win_probability_black
FROM {{ source('stockfish', 'players_games_moves') }} pgm