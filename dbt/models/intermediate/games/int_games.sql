{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_end_time ON {{ this }} (end_time)"
    ]
) }}

{% set elo_range_values = var('elo_range') %}

with incremental_partition as (
    select 
        pg.*
    from {{ ref('stg_chess_com__players_games') }} pg

    {% if is_incremental() %}
    where pg.end_time > (
        select max(i.end_time)
        from {{ this }} i
    )
    {% endif %}
)

, filter_table as (
    select 
        *
    from incremental_partition
    where true 
        and rules = 'chess'     -- Only games respecting this condition are processed by Stockfish
        and (length(initial_setup) = 0 or initial_setup = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1') -- Classic set-up
        and length(pgn) > 0     -- Only games respecting this condition are processed by Stockfish
        and pgn ~ E'\\d+\\. '   -- find at least 1 matching move number, i.e. digit followed by at dot
)

, cast_types as (
    select 
        *,
        end_time::date                  as end_time_date,
        to_char(end_time, 'YYYY-MM')    as end_time_month
    from filter_table    
)

, define_playing as (
    select 
        *,
        case 
            when lower(username) = lower(white__username) then 'White'
            when lower(username) = lower(black__username) then 'Black'
            else null end as playing_as
    from cast_types
)

, define_result as (
    select 
        *,
        case
            when playing_as = 'White' then white__result
            when playing_as = 'Black' then black__result
            else null end as playing_result_detailed,
        case
            when playing_as = 'White' then white__rating
            when playing_as = 'Black' then black__rating
            else null end as playing_rating,
        case
            when playing_as = 'White' then black__rating
            when playing_as = 'Black' then white__rating
            else null end as opponent_rating
    from define_playing
)

, define_rating_range as (
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
    from define_result
)

, simplify_result as (
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