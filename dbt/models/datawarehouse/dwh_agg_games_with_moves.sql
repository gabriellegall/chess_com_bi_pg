{{ config(
    materialized = 'incremental',
    unique_key = ['uuid','username','game_phase'],
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_username ON {{ this }} (username)"
    ]
) }}

{# This variable controls the maximum number of moves that are used to match and integrate the openings hierarchy #}
{% set openings_depth = var('openings')['hierarchy_depth'] + 1 %}  {# use '+1' includes the outer bond for use in the Jinja loop #}

WITH aggregate_fields AS (
    SELECT 
        username,
        uuid,
        game_phase,
        CASE 
            WHEN GROUPING(game_phase) = 1 THEN 'Games'
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
        MIN(eco) AS eco,
        MIN(playing_result) AS playing_result,
        MIN(time_class) AS time_class,
        MIN(time_control) AS time_control,
        
        -- Measures                
        COUNT(move_number) AS nb_moves,
        COUNT(*) FILTER (WHERE miss_category_playing IN ('Blunder', 'Massive Blunder'))                                                                 AS nb_blunder_playing,
        COUNT(*) FILTER (WHERE miss_category_playing = 'Massive Blunder')                                                                               AS nb_massive_blunder_playing,
        COUNT(*) FILTER (WHERE score_playing > {{ var('should_win_range')['mid'] }})                                                                    AS nb_moves_above_decisive_advantage,

            -- % time reamining
        MIN(CASE WHEN miss_category_playing IN ('Blunder', 'Massive Blunder') THEN prct_time_remaining ELSE NULL END)                                   AS first_blunder_playing_prct_time_remaining,
        MIN(CASE WHEN miss_category_playing = 'Massive Blunder' THEN prct_time_remaining ELSE NULL END)                                                 AS first_massive_blunder_playing_prct_time_remaining,
        MIN(CASE WHEN miss_category_playing = 'Massive Blunder' AND miss_context_playing = 'Missed Opportunity' THEN prct_time_remaining ELSE NULL END) AS first_missed_opp_massive_blunder_playing_prct_time_remaining,
        MIN(CASE WHEN miss_category_playing = 'Massive Blunder' AND miss_context_playing = 'Throw' THEN prct_time_remaining ELSE NULL END)              AS first_throw_massive_blunder_playing_prct_time_remaining,        
        {% for phase, values in var('game_phases').items() %}
            {% if 'end_game_move' in values %}
            -- % Time Remaining by game_phase for the playing user. Either exactly at the end of the game phase or 1 move before (depending on the color played).
            MIN(
            CASE 
                WHEN is_playing_turn AND move_number IN ({{ values.end_game_move }}, {{ values.end_game_move }} - 1)
                THEN prct_time_remaining
                ELSE NULL
            END
            ) AS prct_time_remaining_playing_{{ phase }},
            {% endif %}
        {% endfor %}

        STRING_AGG(massive_blunder_move_number_playing::TEXT, ', ') AS massive_blunder_move_number_playing,

        {% set player_prefixes = ['playing', 'opponent'] %}
        {% for prefix in player_prefixes %}
            -- Throws (Blunders and Massive Blunders)
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Throw')                                                                 AS nb_throw_{{ prefix }},
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Throw' AND miss_category_{{ prefix }} = 'Blunder')                      AS nb_throw_blunder_{{ prefix }},
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Throw' AND miss_category_{{ prefix }} = 'Massive Blunder')              AS nb_throw_massive_blunder_{{ prefix }},
            -- Missed Opportunities (Blunders and Massive Blunders)
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Missed Opportunity')                                                    AS nb_missed_opportunity_{{ prefix }},
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Missed Opportunity' AND miss_category_{{ prefix }} = 'Blunder')         AS nb_missed_opportunity_blunder_{{ prefix }},
            COUNT(*) FILTER (WHERE miss_context_{{ prefix }} = 'Missed Opportunity' AND miss_category_{{ prefix }} = 'Massive Blunder') AS nb_missed_opportunity_massive_blunder_{{ prefix }},
            
            {% for phase, values in var('game_phases').items() %}
            -- Blunders and Massive Blunders by game_phase
            COUNT(*) FILTER (WHERE game_phase = {{ values['name'] }} AND miss_category_{{ prefix }} = 'Massive Blunder')                 AS nb_massive_blunder_{{ prefix }}_{{ phase }},
            COUNT(*) FILTER (WHERE game_phase = {{ values['name'] }} AND miss_category_{{ prefix }} IN ('Blunder', 'Massive Blunder'))   AS nb_blunder_{{ prefix }}_{{ phase }},
            
            -- Throws & Missed Opportunities (Blunders and Massive Blunders) by game_phase
            COUNT(*) FILTER (WHERE game_phase = {{ values['name'] }} AND miss_context_{{ prefix }} = 'Missed Opportunity'   AND miss_category_{{ prefix }} = 'Blunder')           AS nb_missed_opportunity_blunder_{{ prefix }}_{{ phase }},
            COUNT(*) FILTER (WHERE game_phase = {{ values['name'] }} AND miss_context_{{ prefix }} = 'Missed Opportunity'   AND miss_category_{{ prefix }} = 'Massive Blunder')   AS nb_missed_opportunity_massive_blunder_{{ prefix }}_{{ phase }},
            COUNT(*) FILTER (WHERE game_phase = {{ values['name'] }} AND miss_context_{{ prefix }} = 'Throw'                AND miss_category_{{ prefix }} = 'Blunder')           AS nb_throw_blunder_{{ prefix }}_{{ phase }},
            COUNT(*) FILTER (WHERE game_phase = {{ values['name'] }} AND miss_context_{{ prefix }} = 'Throw'                AND miss_category_{{ prefix }} = 'Massive Blunder')   AS nb_throw_massive_blunder_{{ prefix }}_{{ phase }},
            {% endfor %}
        {% endfor %}

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
        END AS max_score_playing_type,

        -- Opening Moves
        {% for n in range(1, openings_depth) %}
            STRING_AGG(CASE WHEN move_number <= {{ n }} THEN move ELSE NULL END, ' ' ORDER BY move_number ASC)                          AS opener_{{ n }}_moves
            {% if not loop.last %},{% endif %}
        {% endfor %}

    FROM {{ ref('dwh_games_with_moves') }} games
    {% if is_incremental() %}
    WHERE NOT EXISTS (
        SELECT 1
        FROM {{ this }} i
        WHERE i.uuid = games.uuid
          AND i.username = games.username
    )    
    {% endif %}
    GROUP BY GROUPING SETS (
        (username, uuid, game_phase),
        (username, uuid)
    )
)

, integrate_openings_hierarchy AS (
    SELECT 
        agg.*,
        {% for i in range(1, openings_depth, 1) %}
        -- Among all matched openings, select the most specific opening hierarchy available
            COALESCE(
                {% for j in range(openings_depth - 1, 0, -1) %} -- Deepest to shallowest - i.e. prioritize the most specific opening hierarchy
                    op{{ j }}.uci_hierarchy_level_{{ i }}_name{% if not loop.last %},{% endif %}
                {% endfor %}
                ) AS uci_hierarchy_level_{{ i }}_name
                {% if not loop.last %},{% endif %}
        {% endfor %}
    FROM aggregate_fields agg
    {% for i in range(1, openings_depth, 1) %}
    -- Attempt to match on each and every opening moves
    LEFT OUTER JOIN {{ ref('int_openings') }} op{{ i }}
        ON agg.opener_{{ i }}_moves = op{{ i }}.uci
    {% endfor %}
)

SELECT 
    *
FROM integrate_openings_hierarchy
