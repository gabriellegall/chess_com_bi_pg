{{ config(
    materialized = 'incremental',
    unique_key = ['uuid','game_phase'],
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_username ON {{ this }} (username)"
    ]
) }}
WITH aggregate_fields AS (
    SELECT 
        username,
        uuid,
        game_phase,
        CASE 
            WHEN GROUPING(game_phase) = 1 THEN 'Recent Games'
            ELSE game_phase
        END AS game_phase_key,
        CASE 
            WHEN GROUPING(game_phase) = 1 THEN 'Games'
            ELSE 'Game Phases'
        END AS aggregation_level,

        -- Dimensions
        MIN(url) AS url,
        MIN(end_time) AS end_time,
        MIN(end_time_date) AS end_time_date,
        MIN(end_time_month) AS end_time_month, 
        MIN(playing_rating) AS playing_rating,
        MIN(playing_rating_range) AS playing_rating_range,
        MIN(opponent_rating) AS opponent_rating,
        MIN(opponent_rating_range) AS opponent_rating_range,
        MIN(playing_as) AS playing_as,
        MIN(playing_result) AS playing_result,
        MIN(time_class) AS time_class,
        MIN(time_control) AS time_control,
        MIN(first_blunder_playing_turn_name) AS first_blunder_playing_turn_name,
        
        -- Measures                
        COUNT(move_number) AS nb_moves,
        COUNT(*) FILTER (WHERE miss_category_playing IN ('Blunder', 'Massive Blunder')) AS nb_blunder_playing,
        COUNT(*) FILTER (WHERE miss_category_playing = 'Massive Blunder') AS nb_massive_blunder_playing,
        COUNT(*) FILTER (WHERE score_playing > {{ var('should_win_range')['mid'] }}) AS nb_moves_above_decisive_advantage,
        MIN(CASE WHEN miss_category_playing IN ('Blunder', 'Massive Blunder') THEN prct_time_remaining ELSE NULL END) AS first_blunder_playing_prct_time_remaining,
        MIN(CASE WHEN miss_category_playing = 'Massive Blunder' THEN prct_time_remaining ELSE NULL END) AS first_massive_blunder_playing_prct_time_remaining,

        {% for phase, values in var('game_phases').items() %}
        COUNT(*) FILTER (WHERE game_phase = {{ values['name'] }} AND miss_category_playing = 'Massive Blunder') AS nb_massive_blunder_{{ phase }}_playing,
        COUNT(*) FILTER (WHERE game_phase = {{ values['name'] }} AND miss_category_playing IN ('Blunder', 'Massive Blunder')) AS nb_blunder_{{ phase }}_playing,
        {% endfor %}

        STRING_AGG(massive_blunder_move_number_playing::TEXT, ', ') AS massive_blunder_move_number_playing,
        COUNT(*) FILTER (WHERE miss_context_playing = 'Throw') AS nb_throw_playing,
        COUNT(*) FILTER (WHERE miss_context_playing = 'Missed Opportunity') AS nb_missed_opportunity_playing,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY score_playing) AS median_score_playing,
        MAX(score_playing) AS max_score_playing,
        MIN(score_playing) AS min_score_playing,
        STDDEV_SAMP(score_playing) AS std_score_playing,

        -- Calculated Dimensions
        CASE 
            WHEN MAX(score_playing) < {{ var('should_win_range')['low'] }} THEN '0-{{ var('should_win_range')['low'] }}'
            WHEN MAX(score_playing) < {{ var('should_win_range')['mid'] }} THEN '{{ var('should_win_range')['low'] }}-{{ var('should_win_range')['mid'] }}'
            ELSE '{{ var('should_win_range')['mid'] }}+'
        END AS max_score_playing_range,
        
        CASE    
            WHEN MAX(score_playing) > {{ var('should_win_range')['mid'] }} THEN 'Decisive advantage'
            ELSE 'No decisive advantage'
        END AS max_score_playing_type

    FROM {{ ref('dwh_games_with_moves') }}
    {% if is_incremental() %}
    WHERE uuid NOT IN (SELECT DISTINCT uuid FROM {{ this }})
    {% endif %}
    GROUP BY GROUPING SETS (
        (username, uuid, game_phase),
        (username, uuid)
    )
)

SELECT 
    *,
    (COUNT(*) OVER (
        PARTITION BY username, time_class, end_time_month, opponent_rating_range, game_phase_key
    ) > {{ var('datamart')['min_games_played'] }}) AS has_enough_games
FROM aggregate_fields
