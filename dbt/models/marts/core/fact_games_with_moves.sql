{{ config(
    materialized = 'incremental',
    unique_key = ['uuid','username','move_number'],
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_username ON {{ this }} (username)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

WITH games_scope AS (
  SELECT
    games.uuid,
    games.username,
    games.playing_as
  FROM {{ ref ('int_games') }} games
  WHERE TRUE
    AND end_time_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '{{ var('data_scope')['month_history_depth'] }} months')
    AND time_class = ANY(ARRAY{{ var('data_scope')['time_class'] }}::text[])    
    AND rated
    {% if is_incremental() %}
    -- Game UUID is not already in the target table:
    AND NOT EXISTS (
        SELECT 1
        FROM {{ this }} i
        WHERE i.uuid = games.uuid
          AND i.username = games.username
    )
    {% endif %}
)

, score_defintion AS (
  SELECT 
    games.uuid,
    COALESCE(username_mapping.target_username, games.username) AS username, -- Use the target username from the mapping table if it exists
    games_moves.move_number,
    games_times.time_remaining_seconds,
    games_times.time_remaining_seconds / FIRST_VALUE(games_times.time_remaining_seconds) OVER (PARTITION BY games.uuid, games_moves.player_color_turn ORDER BY games_moves.move_number ASC) AS prct_time_remaining,
    games_moves.move,
    CASE  
      WHEN games_moves.move_number <= {{ var('game_phases')['early']['end_game_move'] }} THEN {{ var('game_phases')['early']['name'] }}
      WHEN games_moves.move_number <= {{ var('game_phases')['mid']['end_game_move'] }} THEN {{ var('game_phases')['mid']['name'] }}
      WHEN games_moves.move_number <= {{ var('game_phases')['late']['end_game_move'] }} THEN {{ var('game_phases')['late']['name'] }}
      ELSE {{ var('game_phases')['very_late']['name'] }} END AS game_phase,
    games_moves.player_color_turn,
    games.playing_as,
    games_moves.player_color_turn = games.playing_as AS is_playing_turn,
    CASE
      WHEN games_moves.player_color_turn = games.playing_as THEN 'Playing Turn'
      ELSE 'Opponent Turn' END AS playing_turn_name,
    CASE 
      WHEN games.playing_as = 'White' THEN games_moves.score_white
      WHEN games.playing_as = 'Black' THEN games_moves.score_black
      ELSE NULL END AS score_playing,
    CURRENT_TIMESTAMP AS log_timestamp
    FROM games_scope AS games
    -- Game UUID has been processed with Stockfish and has move data:
    INNER JOIN {{ ref ('int_games_moves') }} AS games_moves
      ON games_moves.uuid = games.uuid
    -- Game UUID has been processed with time data:
    INNER JOIN {{ ref ('int_games_times') }} AS games_times
      ON games_moves.uuid = games_times.uuid
      AND games_moves.move_number = games_times.move_number
  LEFT OUTER JOIN {{ ref ('username_mapping') }} username_mapping
    ON LOWER(username_mapping.username) = LOWER(games.username) 
)

, previous_score AS (
  SELECT 
    *,
    LAG(score_playing) OVER (PARTITION BY uuid, username ORDER BY move_number ASC)                      AS prev_score_playing,
    score_playing - LAG(score_playing) OVER (PARTITION BY uuid, username ORDER BY move_number ASC)      AS variance_score_playing
  FROM score_defintion
)

, position_definition AS (
  SELECT 
    *,
    -- Playing
    CASE 
      WHEN is_playing_turn 
          AND variance_score_playing <= -{{ var('score_thresholds')['variance_score_massive_blunder'] }} 
          AND prev_score_playing > -{{ var('score_thresholds')['score_balanced_limit'] }} 
          AND score_playing < {{ var('score_thresholds')['score_balanced_limit'] }} 
          THEN 'Massive Blunder'
      WHEN is_playing_turn 
          AND variance_score_playing <= -{{ var('score_thresholds')['variance_score_blunder'] }} 
          AND prev_score_playing > -{{ var('score_thresholds')['score_balanced_limit'] }} 
          AND score_playing < {{ var('score_thresholds')['score_balanced_limit'] }} 
          THEN 'Blunder'
      WHEN is_playing_turn 
          AND variance_score_playing <= -{{ var('score_thresholds')['variance_score_mistake'] }} 
          THEN 'Mistake'
      ELSE NULL END AS miss_category_playing,
    CASE 
      WHEN is_playing_turn 
          AND variance_score_playing <= -{{ var('score_thresholds')['variance_score_mistake'] }} 
          THEN move_number
      ELSE NULL END AS miss_move_number_playing,
    CASE 
      WHEN is_playing_turn 
          AND variance_score_playing <= -{{ var('score_thresholds')['variance_score_massive_blunder'] }} 
          AND prev_score_playing > -{{ var('score_thresholds')['score_balanced_limit'] }} 
          AND score_playing < {{ var('score_thresholds')['score_balanced_limit'] }} 
          THEN move_number
      ELSE NULL END AS massive_blunder_move_number_playing,
    -- Opponent
    CASE
      WHEN NOT is_playing_turn 
          AND variance_score_playing >= {{ var('score_thresholds')['variance_score_massive_blunder'] }} 
          AND prev_score_playing < {{ var('score_thresholds')['score_balanced_limit'] }} 
          AND score_playing > -{{ var('score_thresholds')['score_balanced_limit'] }} 
          THEN 'Massive Blunder'
      WHEN NOT is_playing_turn 
          AND variance_score_playing >= {{ var('score_thresholds')['variance_score_blunder'] }} 
          AND prev_score_playing < {{ var('score_thresholds')['score_balanced_limit'] }} 
          AND score_playing > -{{ var('score_thresholds')['score_balanced_limit'] }} 
          THEN 'Blunder'
      WHEN NOT is_playing_turn 
          AND variance_score_playing >= {{ var('score_thresholds')['variance_score_mistake'] }} 
          THEN 'Mistake'
      ELSE NULL END AS miss_category_opponent,
    CASE 
      WHEN NOT is_playing_turn 
          AND variance_score_playing >= {{ var('score_thresholds')['variance_score_mistake'] }} 
          THEN move_number
      ELSE NULL END AS miss_move_number_opponent,
    -- Position
    CASE  
      WHEN ABS(score_playing) <= {{ var('score_thresholds')['even_score_limit'] }} THEN 'Even'
      WHEN score_playing <= -{{ var('score_thresholds')['even_score_limit'] }} THEN 'Disadvantage'
      WHEN score_playing >= {{ var('score_thresholds')['even_score_limit'] }} THEN 'Advantage'
      ELSE NULL END AS position_status_playing,
    CASE  
      WHEN ABS(score_playing) <= {{ var('score_thresholds')['even_score_limit'] }} THEN 'Even'
      WHEN score_playing <= -{{ var('score_thresholds')['even_score_limit'] }} THEN 'Advantage'   -- Opposite rule compared to _playing
      WHEN score_playing >= {{ var('score_thresholds')['even_score_limit'] }} THEN 'Disadvantage' -- Opposite rule compared to _playing
      ELSE NULL END AS position_status_opponent
  FROM previous_score
)

, prev_position_definition AS (
  SELECT 
    *,
    LAG(position_status_playing)  OVER (PARTITION BY uuid, username ORDER BY move_number ASC) AS prev_position_status_playing,
    LAG(position_status_opponent) OVER (PARTITION BY uuid, username ORDER BY move_number ASC) AS prev_position_status_opponent
  FROM position_definition
)

, context_definition AS (
  SELECT 
    *,
    CASE  
      WHEN miss_category_playing IN ('Blunder', 'Massive Blunder') AND prev_position_status_playing IN ('Even', 'Disadvantage')     THEN 'Throw'
      WHEN miss_category_playing IN ('Blunder', 'Massive Blunder') AND prev_position_status_playing IN ('Advantage')                THEN 'Missed Opportunity' 
      ELSE NULL END AS miss_context_playing,
    CASE  
      WHEN miss_category_opponent IN ('Blunder', 'Massive Blunder') AND prev_position_status_opponent IN ('Even', 'Disadvantage')   THEN 'Throw'
      WHEN miss_category_opponent IN ('Blunder', 'Massive Blunder') AND prev_position_status_opponent IN ('Advantage')              THEN 'Missed Opportunity' 
      ELSE NULL END AS miss_context_opponent
  FROM prev_position_definition
)

SELECT 
  *
FROM context_definition