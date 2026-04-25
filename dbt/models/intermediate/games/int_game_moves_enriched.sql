{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

with games_scope as (
  select
    games.*
  from {{ ref('int_games_filtered') }} as games
  where true
  {% if is_incremental() %}
    and not exists (
      select 1
      from {{ this }} i
      where i.uuid = games.uuid
    )
  {% endif %}
)

, score_definition as (
  select
    games.uuid,
    games.username,
    games.url,
    games.archive_url,
    games.pgn,
    games.time_control,
    games.end_time,
    games.end_time_date,
    games.end_time_month,
    games.rated,
    games.time_class,
    games.rules,
    games.eco,
    games.white__username,
    games.white__rating,
    games.black__username,
    games.black__rating,
    games.playing_as,
    games.playing_result,
    games.playing_rating,
    games.playing_rating_range,
    games.opponent_rating,
    games.opponent_rating_range,
    games_moves.move_number,
    games_moves.move,
    games_times.time_remaining_seconds,
    games_times.time_remaining_seconds / first_value(games_times.time_remaining_seconds) over (
      partition by games.uuid, games_moves.player_color_turn
      order by games_moves.move_number asc
    ) as prct_time_remaining,
    case
      when games_moves.move_number <= {{ var('game_phases')['early']['end_game_move'] }} then {{ var('game_phases')['early']['name'] }}
      when games_moves.move_number <= {{ var('game_phases')['mid']['end_game_move'] }} then {{ var('game_phases')['mid']['name'] }}
      when games_moves.move_number <= {{ var('game_phases')['late']['end_game_move'] }} then {{ var('game_phases')['late']['name'] }}
      else {{ var('game_phases')['very_late']['name'] }}
    end as game_phase,
    games_moves.player_color_turn,
    games_moves.player_color_turn = games.playing_as as is_playing_turn,
    case
      when games_moves.player_color_turn = games.playing_as then 'Playing Turn'
      else 'Opponent Turn'
    end as playing_turn_name,
    case
      when games.playing_as = 'White' then games_moves.score_white
      when games.playing_as = 'Black' then games_moves.score_black
      else null
    end as score_playing,
    case
      when games.playing_as = 'White' then games_moves.win_probability_white
      when games.playing_as = 'Black' then games_moves.win_probability_black
      else null
    end as win_probability_playing,
    current_timestamp as log_timestamp
  from games_scope as games
  inner join {{ ref('int_game_moves_base') }} as games_moves
    on games_moves.uuid = games.uuid
  inner join {{ ref('int_game_move_times_base') }} as games_times
    on games_moves.uuid = games_times.uuid
    and games_moves.move_number = games_times.move_number
)

, previous_score as (
  select
    *,
    lag(score_playing) over (partition by uuid, username order by move_number asc) as prev_score_playing,
    score_playing - lag(score_playing) over (partition by uuid, username order by move_number asc) as variance_score_playing
  from score_definition
)

, position_definition as (
  select
    *,
    case
      when is_playing_turn
        and variance_score_playing <= -{{ var('score_thresholds')['variance_score_massive_blunder'] }}
        and prev_score_playing > -{{ var('score_thresholds')['score_balanced_limit'] }}
        and score_playing < {{ var('score_thresholds')['score_balanced_limit'] }} then 'Massive Blunder'
      when is_playing_turn
        and variance_score_playing <= -{{ var('score_thresholds')['variance_score_blunder'] }}
        and prev_score_playing > -{{ var('score_thresholds')['score_balanced_limit'] }}
        and score_playing < {{ var('score_thresholds')['score_balanced_limit'] }} then 'Blunder'
      when is_playing_turn
        and variance_score_playing <= -{{ var('score_thresholds')['variance_score_mistake'] }} then 'Mistake'
      else null
    end as miss_category_playing,
    case
      when is_playing_turn
        and variance_score_playing <= -{{ var('score_thresholds')['variance_score_mistake'] }} then move_number
      else null
    end as miss_move_number_playing,
    case
      when is_playing_turn
        and variance_score_playing <= -{{ var('score_thresholds')['variance_score_massive_blunder'] }}
        and prev_score_playing > -{{ var('score_thresholds')['score_balanced_limit'] }}
        and score_playing < {{ var('score_thresholds')['score_balanced_limit'] }} then move_number
      else null
    end as massive_blunder_move_number_playing,
    case
      when not is_playing_turn
        and variance_score_playing >= {{ var('score_thresholds')['variance_score_massive_blunder'] }}
        and prev_score_playing < {{ var('score_thresholds')['score_balanced_limit'] }}
        and score_playing > -{{ var('score_thresholds')['score_balanced_limit'] }} then 'Massive Blunder'
      when not is_playing_turn
        and variance_score_playing >= {{ var('score_thresholds')['variance_score_blunder'] }}
        and prev_score_playing < {{ var('score_thresholds')['score_balanced_limit'] }}
        and score_playing > -{{ var('score_thresholds')['score_balanced_limit'] }} then 'Blunder'
      when not is_playing_turn
        and variance_score_playing >= {{ var('score_thresholds')['variance_score_mistake'] }} then 'Mistake'
      else null
    end as miss_category_opponent,
    case
      when not is_playing_turn
        and variance_score_playing >= {{ var('score_thresholds')['variance_score_mistake'] }} then move_number
      else null
    end as miss_move_number_opponent,
    case
      when abs(score_playing) <= {{ var('score_thresholds')['even_score_limit'] }} then 'Even'
      when score_playing <= -{{ var('score_thresholds')['even_score_limit'] }} then 'Disadvantage'
      when score_playing >= {{ var('score_thresholds')['even_score_limit'] }} then 'Advantage'
      else null
    end as position_status_playing,
    case
      when abs(score_playing) <= {{ var('score_thresholds')['even_score_limit'] }} then 'Even'
      when score_playing <= -{{ var('score_thresholds')['even_score_limit'] }} then 'Advantage'
      when score_playing >= {{ var('score_thresholds')['even_score_limit'] }} then 'Disadvantage'
      else null
    end as position_status_opponent
  from previous_score
)

, prev_position_definition as (
  select
    *,
    lag(position_status_playing) over (partition by uuid, username order by move_number asc) as prev_position_status_playing,
    lag(position_status_opponent) over (partition by uuid, username order by move_number asc) as prev_position_status_opponent
  from position_definition
)

, context_definition as (
  select
    *,
    case
      when miss_category_playing in ('Blunder', 'Massive Blunder')
        and prev_position_status_playing in ('Even', 'Disadvantage') then 'Throw'
      when miss_category_playing in ('Blunder', 'Massive Blunder')
        and prev_position_status_playing in ('Advantage') then 'Missed Opportunity'
      else null
    end as miss_context_playing,
    case
      when miss_category_opponent in ('Blunder', 'Massive Blunder')
        and prev_position_status_opponent in ('Even', 'Disadvantage') then 'Throw'
      when miss_category_opponent in ('Blunder', 'Massive Blunder')
        and prev_position_status_opponent in ('Advantage') then 'Missed Opportunity'
      else null
    end as miss_context_opponent
  from prev_position_definition
)

select
  *
from context_definition