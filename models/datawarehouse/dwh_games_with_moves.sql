{{ config(
    materialized = 'incremental',
    unique_key = ['uuid','move_number'],
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)"
    ]
) }}

{% set elo_range_values = var('elo_range') %}

WITH games_scope AS (
  SELECT
    *
  FROM {{ ref ('int_games') }}
  WHERE TRUE
    AND end_time_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '{{ var('data_scope')['month_history_depth'] }} months')
    AND rated
    {% if is_incremental() %}
    AND log_timestamp > (SELECT MAX(log_timestamp) FROM {{ this }})
    {% endif %}
)

, score_defintion AS (
  SELECT 
    games.uuid,
    games.archive_url,
    COALESCE(username_mapping.target_username, games.username) AS username, -- Use the target username from the mapping table if it exists
    games.url,
    games.end_time,
    games.end_time_date,
    games.end_time_month,
    games.time_class,
    games.time_control,
    games.white__username,
    games.white__rating,
    games.black__username,
    games.black__rating,
    games.log_timestamp,
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
    player_color_turn = playing_as AS is_playing_turn,
    CASE
      WHEN player_color_turn = playing_as THEN 'Playing Turn'
      ELSE 'Opponent Turn' END AS playing_turn_name,
    games.playing_rating, 
    CASE 
      {% for idx in range(elo_range_values|length) %}
      WHEN games.playing_rating < {{ elo_range_values[idx] }} THEN 
          '{{ "%04d"|format(elo_range_values[idx-1] if idx > 0 else 0) }}-{{ "%04d"|format(elo_range_values[idx]) }}'
      {% endfor %}
      ELSE '{{ "%04d"|format(elo_range_values[-1]) }}+'
      END AS playing_rating_range,
    games.opponent_rating,
    CASE 
      {% for idx in range(elo_range_values|length) %}
      WHEN games.opponent_rating < {{ elo_range_values[idx] }} THEN 
          '{{ "%04d"|format(elo_range_values[idx-1] if idx > 0 else 0) }}-{{ "%04d"|format(elo_range_values[idx]) }}'
      {% endfor %}
      ELSE '{{ "%04d"|format(elo_range_values[-1]) }}+'
      END AS opponent_rating_range,
    games.playing_result,
    CASE 
      WHEN playing_as = 'White' THEN score_white
      WHEN playing_as = 'Black' THEN score_black
      ELSE NULL END AS score_playing,
    CASE 
      WHEN playing_as = 'White' THEN win_probability_white
      WHEN playing_as = 'Black' THEN win_probability_black
      ELSE NULL END AS win_probability_playing
  FROM games_scope AS games
  LEFT OUTER JOIN {{ ref ('username_mapping') }} username_mapping
    ON LOWER(username_mapping.username) = LOWER(games.username) 
  INNER JOIN {{ ref ('int_games_moves') }} AS games_moves
    USING (uuid)
  LEFT OUTER JOIN {{ ref ('int_games_times') }} games_times
    ON games.uuid = games_times.uuid
    AND games_moves.move_number = games_times.move_number
)

SELECT * FROM score_defintion