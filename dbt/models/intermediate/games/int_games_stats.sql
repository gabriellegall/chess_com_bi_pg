{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook = [
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

WITH agg_definitions AS (
    SELECT
        games.username,
        games.uuid,
        MAX(log_timestamp) AS log_timestamp,

        COUNT(games.move_number) AS nb_moves,
        COUNT(*) FILTER (WHERE games.miss_category_playing IN ('Blunder', 'Massive Blunder')) AS nb_blunder_massive_blunder_playing,
        COUNT(*) FILTER (WHERE games.miss_category_playing = 'Massive Blunder') AS nb_massive_blunder_playing,
        COUNT(*) FILTER (WHERE games.score_playing > {{ var('should_win_range')['mid'] }}) AS nb_moves_above_decisive_advantage,
        {% for snapshot_turn in var('move_stats_snapshots', []) %}
            (
                ARRAY_AGG(games.score_playing ORDER BY games.move_number DESC)
                FILTER (
                    WHERE games.move_number <= {{ snapshot_turn }}
                        AND games.score_playing IS NOT NULL
                )
            )[1] AS score_playing_turn_{{ snapshot_turn }},
        {% endfor %}
        STRING_AGG(massive_blunder_move_number_playing::text, ', ') AS massive_blunder_move_number_playing,
        {% set player_prefixes = ['playing', 'opponent'] %}
        {% for prefix in player_prefixes %}
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Throw') AS nb_throw_{{ prefix }},
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Throw' AND miss_category_{{ prefix }} = 'Blunder') AS nb_throw_blunder_{{ prefix }},
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Throw' AND miss_category_{{ prefix }} = 'Massive Blunder') AS nb_throw_massive_blunder_{{ prefix }},
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Missed Opportunity') AS nb_missed_opportunity_{{ prefix }},
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Missed Opportunity' AND miss_category_{{ prefix }} = 'Blunder') AS nb_missed_opportunity_blunder_{{ prefix }},
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Missed Opportunity' AND miss_category_{{ prefix }} = 'Massive Blunder') AS nb_missed_opportunity_massive_blunder_{{ prefix }},
            {% for phase, values in var('game_phases').items() %}
                COUNT(*) FILTER (WHERE games.game_phase = {{ values['name'] }} AND miss_category_{{ prefix }} = 'Massive Blunder') AS nb_massive_blunder_{{ prefix }}_{{ phase }},
                COUNT(*) FILTER (WHERE games.game_phase = {{ values['name'] }} AND miss_category_{{ prefix }} IN ('Blunder', 'Massive Blunder')) AS nb_blunder_massive_blunder_{{ prefix }}_{{ phase }},
                COUNT(*) FILTER (WHERE games.game_phase = {{ values['name'] }} AND miss_context_{{ prefix }} = 'Missed Opportunity' AND miss_category_{{ prefix }} = 'Blunder') AS nb_missed_opportunity_blunder_{{ prefix }}_{{ phase }},
                COUNT(*) FILTER (WHERE games.game_phase = {{ values['name'] }} AND miss_context_{{ prefix }} = 'Missed Opportunity' AND miss_category_{{ prefix }} = 'Massive Blunder') AS nb_missed_opportunity_massive_blunder_{{ prefix }}_{{ phase }},
                COUNT(*) FILTER (WHERE games.game_phase = {{ values['name'] }} AND miss_context_{{ prefix }} = 'Throw' AND miss_category_{{ prefix }} = 'Blunder') AS nb_throw_blunder_{{ prefix }}_{{ phase }},
                COUNT(*) FILTER (WHERE games.game_phase = {{ values['name'] }} AND miss_context_{{ prefix }} = 'Throw' AND miss_category_{{ prefix }} = 'Massive Blunder') AS nb_throw_massive_blunder_{{ prefix }}_{{ phase }},
            {% endfor %}
        {% endfor %}

        MIN(CASE WHEN games.miss_category_playing IN ('Blunder', 'Massive Blunder') THEN games.prct_time_remaining ELSE NULL END) AS first_blunder_massive_blunder_playing_prct_time_remaining,
        MIN(CASE WHEN games.miss_category_playing = 'Massive Blunder' THEN games.prct_time_remaining ELSE NULL END) AS first_massive_blunder_playing_prct_time_remaining,
        MIN(CASE WHEN games.miss_category_playing = 'Massive Blunder' AND games.miss_context_playing = 'Missed Opportunity' THEN games.prct_time_remaining ELSE NULL END) AS first_missed_opp_massive_blunder_playing_prct_time_remaining,
        MIN(CASE WHEN games.miss_category_playing = 'Massive Blunder' AND games.miss_context_playing = 'Throw' THEN games.prct_time_remaining ELSE NULL END) AS first_throw_massive_blunder_playing_prct_time_remaining,
        {% for phase, values in var('game_phases').items() %}
            {% if 'end_game_move' in values %}
                MIN(
                    CASE
                        WHEN games.is_playing_turn AND games.move_number IN ({{ values.end_game_move }}, {{ values.end_game_move }} - 1)
                            THEN games.prct_time_remaining
                        ELSE NULL
                    END
                ) AS prct_time_remaining_playing_{{ phase }},
            {% endif %}
        {% endfor %}

        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY games.score_playing) AS median_score_playing,
        MAX(games.score_playing) AS max_score_playing,
        MIN(games.score_playing) AS min_score_playing,
        STDDEV_SAMP(games.score_playing) AS std_score_playing,
        CASE
            WHEN MAX(games.score_playing) < {{ var('should_win_range')['low'] }} THEN '0-{{ var('should_win_range')['low'] }}'
            WHEN MAX(games.score_playing) < {{ var('should_win_range')['mid'] }} THEN '{{ var('should_win_range')['low'] }}-{{ var('should_win_range')['mid'] }}'
            ELSE '{{ var('should_win_range')['mid'] }}+'
        END AS max_score_playing_range,
        CASE
            WHEN MAX(games.score_playing) > {{ var('should_win_range')['mid'] }} THEN 'Decisive advantage'
            ELSE 'No decisive advantage'
        END AS max_score_playing_type
    FROM {{ ref('int_game_moves_enriched') }} games
    {% if is_incremental() %}
        WHERE games.log_timestamp > (
            SELECT MAX(i.log_timestamp)
            FROM {{ this }} i
        )
    {% endif %}
    GROUP BY games.username, games.uuid
)

SELECT
    agg_definitions.*,
    CASE WHEN agg_definitions.nb_throw_blunder_playing > 0 THEN 1 ELSE 0 END AS has_throw_blunder_playing,
    CASE WHEN agg_definitions.nb_throw_blunder_playing_early > 0 THEN 1 ELSE 0 END AS has_throw_blunder_playing_early,
    CASE WHEN agg_definitions.nb_throw_blunder_playing_mid > 0 THEN 1 ELSE 0 END AS has_throw_blunder_playing_mid,
    CASE WHEN agg_definitions.nb_throw_blunder_playing_late > 0 THEN 1 ELSE 0 END AS has_throw_blunder_playing_late,
    CASE WHEN agg_definitions.nb_throw_massive_blunder_playing > 0 THEN 1 ELSE 0 END AS has_throw_massive_blunder_playing,
    CASE WHEN agg_definitions.nb_throw_massive_blunder_playing_early > 0 THEN 1 ELSE 0 END AS has_throw_massive_blunder_playing_early,
    CASE WHEN agg_definitions.nb_throw_massive_blunder_playing_mid > 0 THEN 1 ELSE 0 END AS has_throw_massive_blunder_playing_mid,
    CASE WHEN agg_definitions.nb_throw_massive_blunder_playing_late > 0 THEN 1 ELSE 0 END AS has_throw_massive_blunder_playing_late,
    CASE WHEN agg_definitions.nb_missed_opportunity_blunder_playing > 0 THEN 1 ELSE 0 END AS has_missed_opportunity_blunder_playing,
    CASE WHEN agg_definitions.nb_missed_opportunity_blunder_playing_early > 0 THEN 1 ELSE 0 END AS has_missed_opportunity_blunder_playing_early,
    CASE WHEN agg_definitions.nb_missed_opportunity_blunder_playing_mid > 0 THEN 1 ELSE 0 END AS has_missed_opportunity_blunder_playing_mid,
    CASE WHEN agg_definitions.nb_missed_opportunity_blunder_playing_late > 0 THEN 1 ELSE 0 END AS has_missed_opportunity_blunder_playing_late,
    CASE WHEN agg_definitions.nb_missed_opportunity_massive_blunder_playing > 0 THEN 1 ELSE 0 END AS has_missed_opportunity_massive_blunder_playing,
    CASE WHEN agg_definitions.nb_missed_opportunity_massive_blunder_playing_early > 0 THEN 1 ELSE 0 END AS has_missed_opportunity_massive_blunder_playing_early,
    CASE WHEN agg_definitions.nb_missed_opportunity_massive_blunder_playing_mid > 0 THEN 1 ELSE 0 END AS has_missed_opportunity_massive_blunder_playing_mid,
    CASE WHEN agg_definitions.nb_missed_opportunity_massive_blunder_playing_late > 0 THEN 1 ELSE 0 END AS has_missed_opportunity_massive_blunder_playing_late
FROM agg_definitions