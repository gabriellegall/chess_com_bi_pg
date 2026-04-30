{{ config(materialized = 'view') }}

SELECT
    pgm.*,
    CASE WHEN MOD(pgm.move_number, 2) = 1 THEN 'White' ELSE 'Black' END AS player_color_turn,
    -pgm.score_white AS score_black
FROM {{ source('stockfish', 'players_games_moves') }} pgm