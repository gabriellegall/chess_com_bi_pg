{{ config(warn_if = '>1', error_if = '>10') }}

WITH agg_game AS (
  SELECT 
    username,
    uuid,
    MIN(pgn) AS pgn
  FROM {{ ref ('int_games') }}
  GROUP BY username, uuid
)

, agg_moves AS (
  SELECT
    uuid,
    COUNT(*) AS nb_moves
  FROM {{ ref ('int_games_moves') }}
  GROUP BY uuid
)

, extract_moves_count AS (
  SELECT 
    agg_game.*,
    agg_moves.nb_moves,
    -- Player 1
    (SELECT MAX((m[1])::int) 
     FROM regexp_matches(agg_game.pgn, E'(\\d+)\\. ', 'g') AS m) AS nb_move_p1,
    -- Player 2
    (SELECT MAX((m[1])::int) 
     FROM regexp_matches(agg_game.pgn, E'(\\d+)\\.\\.\\. ', 'g') AS m) AS nb_move_p2
  FROM agg_game
  LEFT JOIN agg_moves USING (uuid)
)

SELECT *
FROM extract_moves_count
-- Player 1 moves + Player 2 moves = Expected total moves
WHERE COALESCE(nb_move_p1, 0) + COALESCE(nb_move_p2, 0) <> COALESCE(nb_moves, 0)