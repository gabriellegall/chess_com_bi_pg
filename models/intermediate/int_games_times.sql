{{ config(enabled=false) }}

{# WITH games_times AS (
  SELECT 
    g.username,
    g.uuid AS game_uuid,
    match[1] AS game_time -- each match as a separate row, e.g. '{[%clk 1:23:45.67]}'
  FROM {{ source('chess_com', 'players_games') }} g
  CROSS JOIN LATERAL regexp_matches(g.pgn, '\{\[%clk [^\]]+\]\}', 'g') AS match
),

extract_time AS (
  SELECT 
    username,
    game_uuid,
    game_time,
    substring(game_time FROM '\{\[%clk ([^\]]+)\]\}') AS time_remaining,
    CAST(substring(game_time FROM '\{\[%clk (\d{1,2}):') AS INTEGER) AS time_part_remaining_hours,
    CAST(substring(game_time FROM '\{\[%clk \d{1,2}:(\d{2}):') AS INTEGER) AS time_part_remaining_minutes,
    CAST(substring(game_time FROM '\{\[%clk \d{1,2}:\d{2}:(\d{2}(?:\.\d+)?)\}') AS NUMERIC) AS time_part_remaining_seconds
  FROM games_times
)

SELECT * FROM extract_time  #}