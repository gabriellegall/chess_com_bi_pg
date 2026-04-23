{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

with agg_definitions as (
    select
        username,
        uuid,
        max(log_timestamp) as log_timestamp,

        count(move_number) as nb_moves,
        count(*) filter (where miss_category_playing in ('Blunder', 'Massive Blunder')) as nb_blunder_massive_blunder_playing,
        count(*) filter (where miss_category_playing = 'Massive Blunder') as nb_massive_blunder_playing,
        count(*) filter (where score_playing > {{ var('should_win_range')['mid'] }}) as nb_moves_above_decisive_advantage,
        string_agg(massive_blunder_move_number_playing::text, ', ') as massive_blunder_move_number_playing,
        {% set player_prefixes = ['playing', 'opponent'] %}
        {% for prefix in player_prefixes %}
            count(*) filter (where miss_context_{{ prefix }} = 'Throw') as nb_throw_{{ prefix }},
            count(*) filter (where miss_context_{{ prefix }} = 'Throw' and miss_category_{{ prefix }} = 'Blunder') as nb_throw_blunder_{{ prefix }},
            count(*) filter (where miss_context_{{ prefix }} = 'Throw' and miss_category_{{ prefix }} = 'Massive Blunder') as nb_throw_massive_blunder_{{ prefix }},
            count(*) filter (where miss_context_{{ prefix }} = 'Missed Opportunity') as nb_missed_opportunity_{{ prefix }},
            count(*) filter (where miss_context_{{ prefix }} = 'Missed Opportunity' and miss_category_{{ prefix }} = 'Blunder') as nb_missed_opportunity_blunder_{{ prefix }},
            count(*) filter (where miss_context_{{ prefix }} = 'Missed Opportunity' and miss_category_{{ prefix }} = 'Massive Blunder') as nb_missed_opportunity_massive_blunder_{{ prefix }},
            {% for phase, values in var('game_phases').items() %}
            count(*) filter (where game_phase = {{ values['name'] }} and miss_category_{{ prefix }} = 'Massive Blunder') as nb_massive_blunder_{{ prefix }}_{{ phase }},
            count(*) filter (where game_phase = {{ values['name'] }} and miss_category_{{ prefix }} in ('Blunder', 'Massive Blunder')) as nb_blunder_massive_blunder_{{ prefix }}_{{ phase }},
            count(*) filter (where game_phase = {{ values['name'] }} and miss_context_{{ prefix }} = 'Missed Opportunity' and miss_category_{{ prefix }} = 'Blunder') as nb_missed_opportunity_blunder_{{ prefix }}_{{ phase }},
            count(*) filter (where game_phase = {{ values['name'] }} and miss_context_{{ prefix }} = 'Missed Opportunity' and miss_category_{{ prefix }} = 'Massive Blunder') as nb_missed_opportunity_massive_blunder_{{ prefix }}_{{ phase }},
            count(*) filter (where game_phase = {{ values['name'] }} and miss_context_{{ prefix }} = 'Throw' and miss_category_{{ prefix }} = 'Blunder') as nb_throw_blunder_{{ prefix }}_{{ phase }},
            count(*) filter (where game_phase = {{ values['name'] }} and miss_context_{{ prefix }} = 'Throw' and miss_category_{{ prefix }} = 'Massive Blunder') as nb_throw_massive_blunder_{{ prefix }}_{{ phase }},
            {% endfor %}
        {% endfor %}

        min(case when miss_category_playing in ('Blunder', 'Massive Blunder') then prct_time_remaining else null end) as first_blunder_massive_blunder_playing_prct_time_remaining,
        min(case when miss_category_playing = 'Massive Blunder' then prct_time_remaining else null end) as first_massive_blunder_playing_prct_time_remaining,
        min(case when miss_category_playing = 'Massive Blunder' and miss_context_playing = 'Missed Opportunity' then prct_time_remaining else null end) as first_missed_opp_massive_blunder_playing_prct_time_remaining,
        min(case when miss_category_playing = 'Massive Blunder' and miss_context_playing = 'Throw' then prct_time_remaining else null end) as first_throw_massive_blunder_playing_prct_time_remaining,
        {% for phase, values in var('game_phases').items() %}
            {% if 'end_game_move' in values %}
            min(
            case
                when is_playing_turn and move_number in ({{ values.end_game_move }}, {{ values.end_game_move }} - 1)
                then prct_time_remaining
                else null
            end
            ) as prct_time_remaining_playing_{{ phase }},
            {% endif %}
        {% endfor %}

        percentile_cont(0.5) within group (order by score_playing) as median_score_playing,
        max(score_playing) as max_score_playing,
        min(score_playing) as min_score_playing,
        stddev_samp(score_playing) as std_score_playing,
        case
            when max(score_playing) < {{ var('should_win_range')['low'] }} then '0-{{ var('should_win_range')['low'] }}'
            when max(score_playing) < {{ var('should_win_range')['mid'] }} then '{{ var('should_win_range')['low'] }}-{{ var('should_win_range')['mid'] }}'
            else '{{ var('should_win_range')['mid'] }}+'
        end as max_score_playing_range,
        case
            when max(score_playing) > {{ var('should_win_range')['mid'] }} then 'Decisive advantage'
            else 'No decisive advantage'
        end as max_score_playing_type
    from {{ ref('int_games_with_moves_enriched') }} games
    {% if is_incremental() %}
    where games.log_timestamp > (
        select max(i.log_timestamp)
        from {{ this }} i
    )
    {% endif %}
    group by username, uuid
)

select
    agg_definitions.*,
    case when nb_throw_blunder_playing > 0 then 1 else 0 end as has_throw_blunder_playing,
    case when nb_throw_blunder_playing_early > 0 then 1 else 0 end as has_throw_blunder_playing_early,
    case when nb_throw_blunder_playing_mid > 0 then 1 else 0 end as has_throw_blunder_playing_mid,
    case when nb_throw_blunder_playing_late > 0 then 1 else 0 end as has_throw_blunder_playing_late,
    case when nb_throw_massive_blunder_playing > 0 then 1 else 0 end as has_throw_massive_blunder_playing,
    case when nb_throw_massive_blunder_playing_early > 0 then 1 else 0 end as has_throw_massive_blunder_playing_early,
    case when nb_throw_massive_blunder_playing_mid > 0 then 1 else 0 end as has_throw_massive_blunder_playing_mid,
    case when nb_throw_massive_blunder_playing_late > 0 then 1 else 0 end as has_throw_massive_blunder_playing_late,
    case when nb_missed_opportunity_blunder_playing > 0 then 1 else 0 end as has_missed_opportunity_blunder_playing,
    case when nb_missed_opportunity_blunder_playing_early > 0 then 1 else 0 end as has_missed_opportunity_blunder_playing_early,
    case when nb_missed_opportunity_blunder_playing_mid > 0 then 1 else 0 end as has_missed_opportunity_blunder_playing_mid,
    case when nb_missed_opportunity_blunder_playing_late > 0 then 1 else 0 end as has_missed_opportunity_blunder_playing_late,
    case when nb_missed_opportunity_massive_blunder_playing > 0 then 1 else 0 end as has_missed_opportunity_massive_blunder_playing,
    case when nb_missed_opportunity_massive_blunder_playing_early > 0 then 1 else 0 end as has_missed_opportunity_massive_blunder_playing_early,
    case when nb_missed_opportunity_massive_blunder_playing_mid > 0 then 1 else 0 end as has_missed_opportunity_massive_blunder_playing_mid,
    case when nb_missed_opportunity_massive_blunder_playing_late > 0 then 1 else 0 end as has_missed_opportunity_massive_blunder_playing_late
from agg_definitions