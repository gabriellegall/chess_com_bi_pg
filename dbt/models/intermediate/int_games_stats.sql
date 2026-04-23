{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

WITH agg_definitions AS (
    SELECT
        username,
        uuid,
        MAX(log_timestamp) AS log_timestamp,

        COUNT(move_number) AS nb_moves,
        COUNT(*) FILTER (WHERE miss_category_playing IN ('Blunder', 'Massive Blunder')) AS nb_blunder_massive_blunder_playing,
        COUNT(*) FILTER (WHERE miss_category_playing = 'Massive Blunder') AS nb_massive_blunder_playing,
        COUNT(*) FILTER (WHERE score_playing > {{ var('should_win_range')['mid'] }}) AS nb_moves_above_decisive_advantage,
        STRING_AGG(massive_blunder_move_number_playing::TEXT, ', ') AS massive_blunder_move_number_playing,
        {% set player_prefixes = ['playing', 'opponent'] %}
        {% for prefix in player_prefixes %}
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Throw') AS nb_throw_{{ prefix }},
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Throw' AND miss_category_{{ prefix }} = 'Blunder') AS nb_throw_blunder_{{ prefix }},
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Throw' AND miss_category_{{ prefix }} = 'Massive Blunder') AS nb_throw_massive_blunder_{{ prefix }},
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Missed Opportunity') AS nb_missed_opportunity_{{ prefix }},
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Missed Opportunity' AND miss_category_{{ prefix }} = 'Blunder') AS nb_missed_opportunity_blunder_{{ prefix }},
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Missed Opportunity' AND miss_category_{{ prefix }} = 'Massive Blunder') AS nb_missed_opportunity_massive_blunder_{{ prefix }},
            {% for phase, values in var('game_phases').items() %}
            COUNT(*) FILTER (WHERE game_phase = {{ values['name'] }} AND miss_category_{{ prefix }} = 'Massive Blunder') AS nb_massive_blunder_{{ prefix }}_{{ phase }},
            COUNT(*) FILTER (WHERE game_phase = {{ values['name'] }} AND miss_category_{{ prefix }} IN ('Blunder', 'Massive Blunder')) AS nb_blunder_massive_blunder_{{ prefix }}_{{ phase }},
            COUNT(*) FILTER (WHERE game_phase = {{ values['name'] }} AND miss_context_{{ prefix }} = 'Missed Opportunity' AND miss_category_{{ prefix }} = 'Blunder') AS nb_missed_opportunity_blunder_{{ prefix }}_{{ phase }},
            COUNT(*) FILTER (WHERE game_phase = {{ values['name'] }} AND miss_context_{{ prefix }} = 'Missed Opportunity' AND miss_category_{{ prefix }} = 'Massive Blunder') AS nb_missed_opportunity_massive_blunder_{{ prefix }}_{{ phase }},
            COUNT(*) FILTER (WHERE game_phase = {{ values['name'] }} AND miss_context_{{ prefix }} = 'Throw' AND miss_category_{{ prefix }} = 'Blunder') AS nb_throw_blunder_{{ prefix }}_{{ phase }},
            COUNT(*) FILTER (WHERE game_phase = {{ values['name'] }} AND miss_context_{{ prefix }} = 'Throw' AND miss_category_{{ prefix }} = 'Massive Blunder') AS nb_throw_massive_blunder_{{ prefix }}_{{ phase }},
            {% endfor %}
        {% endfor %}

        MIN(CASE WHEN miss_category_playing IN ('Blunder', 'Massive Blunder') THEN prct_time_remaining ELSE NULL END) AS first_blunder_massive_blunder_playing_prct_time_remaining,
        MIN(CASE WHEN miss_category_playing = 'Massive Blunder' THEN prct_time_remaining ELSE NULL END) AS first_massive_blunder_playing_prct_time_remaining,
        MIN(CASE WHEN miss_category_playing = 'Massive Blunder' AND miss_context_playing = 'Missed Opportunity' THEN prct_time_remaining ELSE NULL END) AS first_missed_opp_massive_blunder_playing_prct_time_remaining,
        MIN(CASE WHEN miss_category_playing = 'Massive Blunder' AND miss_context_playing = 'Throw' THEN prct_time_remaining ELSE NULL END) AS first_throw_massive_blunder_playing_prct_time_remaining,
        {% for phase, values in var('game_phases').items() %}
            {% if 'end_game_move' in values %}
            MIN(
            CASE
                WHEN is_playing_turn AND move_number IN ({{ values.end_game_move }}, {{ values.end_game_move }} - 1)
                THEN prct_time_remaining
                ELSE NULL
            END
            ) AS prct_time_remaining_playing_{{ phase }},
            {% endif %}
        {% endfor %}

        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY score_playing) AS median_score_playing,
        MAX(score_playing) AS max_score_playing,
        MIN(score_playing) AS min_score_playing,
        STDDEV_SAMP(score_playing) AS std_score_playing,
        CASE
            WHEN MAX(score_playing) < {{ var('should_win_range')['low'] }} THEN '0-{{ var('should_win_range')['low'] }}'
            WHEN MAX(score_playing) < {{ var('should_win_range')['mid'] }} THEN '{{ var('should_win_range')['low'] }}-{{ var('should_win_range')['mid'] }}'
            ELSE '{{ var('should_win_range')['mid'] }}+'
        END AS max_score_playing_range,
        CASE
            WHEN MAX(score_playing) > {{ var('should_win_range')['mid'] }} THEN 'Decisive advantage'
            ELSE 'No decisive advantage'
        END AS max_score_playing_type
    FROM {{ ref('int_games_with_moves_enriched') }} games
    {% if is_incremental() %}
    WHERE games.log_timestamp > (
        SELECT MAX(i.log_timestamp)
        FROM {{ this }} i
    )
    {% endif %}
    GROUP BY username, uuid
)

SELECT
    agg_definitions.*,
    CASE WHEN nb_throw_blunder_playing > 0 THEN 1 ELSE 0 END AS has_throw_blunder_playing,
    CASE WHEN nb_throw_blunder_playing_early > 0 THEN 1 ELSE 0 END AS has_throw_blunder_playing_early,
    CASE WHEN nb_throw_blunder_playing_mid > 0 THEN 1 ELSE 0 END AS has_throw_blunder_playing_mid,
    CASE WHEN nb_throw_blunder_playing_late > 0 THEN 1 ELSE 0 END AS has_throw_blunder_playing_late,
    CASE WHEN nb_throw_massive_blunder_playing > 0 THEN 1 ELSE 0 END AS has_throw_massive_blunder_playing,
    CASE WHEN nb_throw_massive_blunder_playing_early > 0 THEN 1 ELSE 0 END AS has_throw_massive_blunder_playing_early,
    CASE WHEN nb_throw_massive_blunder_playing_mid > 0 THEN 1 ELSE 0 END AS has_throw_massive_blunder_playing_mid,
    CASE WHEN nb_throw_massive_blunder_playing_late > 0 THEN 1 ELSE 0 END AS has_throw_massive_blunder_playing_late,
    CASE WHEN nb_missed_opportunity_blunder_playing > 0 THEN 1 ELSE 0 END AS has_missed_opportunity_blunder_playing,
    CASE WHEN nb_missed_opportunity_blunder_playing_early > 0 THEN 1 ELSE 0 END AS has_missed_opportunity_blunder_playing_early,
    CASE WHEN nb_missed_opportunity_blunder_playing_mid > 0 THEN 1 ELSE 0 END AS has_missed_opportunity_blunder_playing_mid,
    CASE WHEN nb_missed_opportunity_blunder_playing_late > 0 THEN 1 ELSE 0 END AS has_missed_opportunity_blunder_playing_late,
    CASE WHEN nb_missed_opportunity_massive_blunder_playing > 0 THEN 1 ELSE 0 END AS has_missed_opportunity_massive_blunder_playing,
    CASE WHEN nb_missed_opportunity_massive_blunder_playing_early > 0 THEN 1 ELSE 0 END AS has_missed_opportunity_massive_blunder_playing_early,
    CASE WHEN nb_missed_opportunity_massive_blunder_playing_mid > 0 THEN 1 ELSE 0 END AS has_missed_opportunity_massive_blunder_playing_mid,
    CASE WHEN nb_missed_opportunity_massive_blunder_playing_late > 0 THEN 1 ELSE 0 END AS has_missed_opportunity_massive_blunder_playing_late
FROM agg_definitions
