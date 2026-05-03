{{ config(warn_if = '>1', error_if = '>50', enabled = true) }}

WITH agg_game AS (
  SELECT DISTINCT -- uuid is only unique per [username]
    uuid
  FROM {{ ref ('int_games_filtered') }}
)

, agg_times AS (
  SELECT
    uuid,
    MAX(move_number) AS max_move_number_times,
    MIN(move_number) AS min_move_number_times
  FROM {{ ref ('int_game_move_times_base') }}
  INNER JOIN agg_game -- keep only relevant games
    USING (uuid)
  GROUP BY 1
)

, agg_moves AS (
  SELECT
    uuid,
    MAX(move_number) AS max_move_number_moves,
    MIN(move_number) AS min_move_number_moves
  FROM {{ ref ('int_game_moves_base') }}
  INNER JOIN agg_game -- keep only relevant games
    USING (uuid)
  GROUP BY 1
)

SELECT * FROM agg_times
FULL OUTER JOIN agg_moves
  USING (uuid)
WHERE TRUE  
  AND COALESCE(max_move_number_times,0) <> COALESCE(max_move_number_moves,0)
  OR COALESCE(min_move_number_times,0) <> COALESCE(min_move_number_moves,0)