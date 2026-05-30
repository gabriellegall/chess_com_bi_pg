{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook = [
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_run_timestamp ON {{ this }} (run_timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)",
    ]
) }}

{# 
    ### Update strategy explanation:
    - Incremental appends are UUID-driven: on incremental runs, only games whose UUID does not already exist in this model are considered. Rows are inserted only when the INNER JOIN with moves and time tables returns matching move rows.
    - run_timestamp is set to current_timestamp at load time. Unlike log_timestamp (which tracks Python processing time in upstream models), run_timestamp reflects when dbt inserted this row, and drives incremental updates in all downstream models.
#}

WITH games_scope AS (
    SELECT
        games.uuid,
        games.username,
        games.playing_as
    FROM {{ ref('int_games_filtered') }} AS games
    WHERE
        TRUE
        {% if is_incremental() %}
            AND NOT EXISTS (
                SELECT 1
                FROM {{ this }} i
                WHERE i.uuid = games.uuid
            )
        {% endif %}
)

, score_definition AS (
    SELECT
        games.uuid,
        games.username,
        games.playing_as,
        games_moves.move_number,
        games_moves.move,
        games_times.time_remaining_seconds,
        games_times.time_remaining_seconds / FIRST_VALUE(games_times.time_remaining_seconds) OVER (
            PARTITION BY games.uuid, games_moves.player_color_turn
            ORDER BY games_moves.move_number ASC
        ) AS prct_time_remaining,
        CASE
            WHEN games_moves.move_number <= {{ var('game_phases')['early']['end_game_move'] }} THEN {{ var('game_phases')['early']['name'] }}
            WHEN games_moves.move_number <= {{ var('game_phases')['mid']['end_game_move'] }} THEN {{ var('game_phases')['mid']['name'] }}
            WHEN games_moves.move_number <= {{ var('game_phases')['late']['end_game_move'] }} THEN {{ var('game_phases')['late']['name'] }}
            ELSE {{ var('game_phases')['very_late']['name'] }}
        END AS game_phase,
        games_moves.player_color_turn,
        games_moves.player_color_turn = games.playing_as AS is_playing_turn,
        CASE
            WHEN games_moves.player_color_turn = games.playing_as THEN 'Playing Turn'
            ELSE 'Opponent Turn'
        END AS playing_turn_name,
        CASE
            WHEN games.playing_as = 'White' THEN games_moves.score_white
            WHEN games.playing_as = 'Black' THEN games_moves.score_black
            ELSE NULL
        END AS score_playing,
        CURRENT_TIMESTAMP AS run_timestamp
    FROM games_scope AS games
    INNER JOIN {{ ref('int_game_moves_base') }} AS games_moves
        ON games_moves.uuid = games.uuid
    INNER JOIN {{ ref('int_game_move_times_base') }} AS games_times
        ON
            games_moves.uuid = games_times.uuid
            AND games_moves.move_number = games_times.move_number
)

, previous_score AS (
    SELECT
        *,
        LAG(score_playing) OVER (PARTITION BY uuid, username ORDER BY move_number ASC) AS prev_score_playing,
        score_playing - LAG(score_playing) OVER (PARTITION BY uuid, username ORDER BY move_number ASC) AS variance_score_playing
    FROM score_definition
)

, position_definition AS (
    SELECT
        *,
        CASE
            WHEN
                is_playing_turn
                AND variance_score_playing <= -{{ var('score_thresholds')['variance_score_massive_blunder'] }}
                AND prev_score_playing > -{{ var('score_thresholds')['score_balanced_limit'] }}
                AND score_playing < {{ var('score_thresholds')['score_balanced_limit'] }} THEN 'Massive Blunder'
            WHEN
                is_playing_turn
                AND variance_score_playing <= -{{ var('score_thresholds')['variance_score_blunder'] }}
                AND prev_score_playing > -{{ var('score_thresholds')['score_balanced_limit'] }}
                AND score_playing < {{ var('score_thresholds')['score_balanced_limit'] }} THEN 'Blunder'
            WHEN
                is_playing_turn
                AND variance_score_playing <= -{{ var('score_thresholds')['variance_score_mistake'] }} THEN 'Mistake'
            ELSE NULL
        END AS miss_category_playing,
        CASE
            WHEN
                is_playing_turn
                AND variance_score_playing <= -{{ var('score_thresholds')['variance_score_mistake'] }} THEN move_number
            ELSE NULL
        END AS miss_move_number_playing,
        CASE
            WHEN
                is_playing_turn
                AND variance_score_playing <= -{{ var('score_thresholds')['variance_score_massive_blunder'] }}
                AND prev_score_playing > -{{ var('score_thresholds')['score_balanced_limit'] }}
                AND score_playing < {{ var('score_thresholds')['score_balanced_limit'] }} THEN move_number
            ELSE NULL
        END AS massive_blunder_move_number_playing,
        CASE
            WHEN
                NOT is_playing_turn
                AND variance_score_playing >= {{ var('score_thresholds')['variance_score_massive_blunder'] }}
                AND prev_score_playing < {{ var('score_thresholds')['score_balanced_limit'] }}
                AND score_playing > -{{ var('score_thresholds')['score_balanced_limit'] }} THEN 'Massive Blunder'
            WHEN
                NOT is_playing_turn
                AND variance_score_playing >= {{ var('score_thresholds')['variance_score_blunder'] }}
                AND prev_score_playing < {{ var('score_thresholds')['score_balanced_limit'] }}
                AND score_playing > -{{ var('score_thresholds')['score_balanced_limit'] }} THEN 'Blunder'
            WHEN
                NOT is_playing_turn
                AND variance_score_playing >= {{ var('score_thresholds')['variance_score_mistake'] }} THEN 'Mistake'
            ELSE NULL
        END AS miss_category_opponent,
        CASE
            WHEN
                NOT is_playing_turn
                AND variance_score_playing >= {{ var('score_thresholds')['variance_score_mistake'] }} THEN move_number
            ELSE NULL
        END AS miss_move_number_opponent,
        CASE
            WHEN ABS(score_playing) <= {{ var('score_thresholds')['even_score_limit'] }} THEN 'Even'
            WHEN score_playing <= -{{ var('score_thresholds')['even_score_limit'] }} THEN 'Disadvantage'
            WHEN score_playing >= {{ var('score_thresholds')['even_score_limit'] }} THEN 'Advantage'
            ELSE NULL
        END AS position_status_playing,
        CASE
            WHEN ABS(score_playing) <= {{ var('score_thresholds')['even_score_limit'] }} THEN 'Even'
            WHEN score_playing <= -{{ var('score_thresholds')['even_score_limit'] }} THEN 'Advantage'
            WHEN score_playing >= {{ var('score_thresholds')['even_score_limit'] }} THEN 'Disadvantage'
            ELSE NULL
        END AS position_status_opponent
    FROM previous_score
)

, prev_position_definition AS (
    SELECT
        *,
        LAG(position_status_playing) OVER (PARTITION BY uuid, username ORDER BY move_number ASC) AS prev_position_status_playing,
        LAG(position_status_opponent) OVER (PARTITION BY uuid, username ORDER BY move_number ASC) AS prev_position_status_opponent
    FROM position_definition
)

, context_definition AS (
    SELECT
        *,
        CASE
            WHEN
                miss_category_playing IN ('Blunder', 'Massive Blunder')
                AND prev_position_status_playing IN ('Even', 'Disadvantage') THEN 'Throw'
            WHEN
                miss_category_playing IN ('Blunder', 'Massive Blunder')
                AND prev_position_status_playing IN ('Advantage') THEN 'Missed Opportunity'
            ELSE NULL
        END AS miss_context_playing,
        CASE
            WHEN
                miss_category_opponent IN ('Blunder', 'Massive Blunder')
                AND prev_position_status_opponent IN ('Even', 'Disadvantage') THEN 'Throw'
            WHEN
                miss_category_opponent IN ('Blunder', 'Massive Blunder')
                AND prev_position_status_opponent IN ('Advantage') THEN 'Missed Opportunity'
            ELSE NULL
        END AS miss_context_opponent
    FROM prev_position_definition
)

SELECT
    *
FROM context_definition