{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_end_time ON {{ this }} (end_time)"
    ]
) }}

{% set elo_range_values = var('elo_range') %}

with incremental_partition as (
    select 
        pg.end_time,
        pg.url,
        pg.pgn,
        pg.time_control,
        pg.rated,
        pg.tcn,
        pg.uuid,
        pg.initial_setup,
        pg.fen,
        pg.time_class,
        pg.rules,
        pg.white__rating,
        pg.white__result,
        pg.white__aid,
        pg.white__username,
        pg.white__uuid,
        pg.black__rating,
        pg.black__result,
        pg.black__aid,
        pg.black__username,
        pg.black__uuid,
        pg.eco,
        pg.username,
        pg.archive_url,
        pg.log_timestamp,
        pg.accuracies__white,
        pg.accuracies__black,
        pg.start_time,
        pg.tournament,
        pg.end_time_date,
        pg.end_time_month,
        pg.playing_as,
        pg.playing_result_detailed,
        pg.playing_rating,
        pg.opponent_rating
    from {{ ref('stg_chess_com__players_games') }} pg
    {% if is_incremental() %}
        where pg.end_time > (
                select max(i.end_time)
                from {{ this }} i
        )
    {% endif %}
),

define_rating_range as (
    select
        *,
        case
            {% for idx in range(elo_range_values|length) %}
            when playing_rating < {{ elo_range_values[idx] }} then
                '{{ "%04d"|format(elo_range_values[idx-1] if idx > 0 else 0) }}-{{ "%04d"|format(elo_range_values[idx]) }}'
            {% endfor %}
            else '{{ "%04d"|format(elo_range_values[-1]) }}+'
        end as playing_rating_range,
        case
            {% for idx in range(elo_range_values|length) %}
            when opponent_rating < {{ elo_range_values[idx] }} then
                '{{ "%04d"|format(elo_range_values[idx-1] if idx > 0 else 0) }}-{{ "%04d"|format(elo_range_values[idx]) }}'
            {% endfor %}
            else '{{ "%04d"|format(elo_range_values[-1]) }}+'
        end as opponent_rating_range
    from incremental_partition
),

simplify_result as (
    select 
        *,
        case    
            when playing_result_detailed in ('checkmated', 'resigned', 'abandoned', 'timeout')                                      then 'Lose'
            when playing_result_detailed in ('win')                                                                                 then 'Win'
            when playing_result_detailed in ('stalemate', 'repetition', 'agreed', 'timevsinsufficient', 'insufficient', '50move')   then 'Draw'
            else null end as playing_result
    from define_rating_range
)

select 
    * 
from simplify_result