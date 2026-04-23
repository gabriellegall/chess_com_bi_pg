{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_end_time ON {{ this }} (end_time)"
    ]
) }}

{% set elo_range_values = var('elo_range') %}

WITH incremental_partition AS (
    SELECT 
        pg.*
    FROM {{ ref('stg_chess_com__players_games') }} pg

    {% if is_incremental() %}
    WHERE pg.end_time > (
        SELECT MAX(i.end_time)
        FROM {{ this }} i
    )
    {% endif %}
)

, filter_table AS (
    SELECT 
        *
    FROM incremental_partition
    WHERE TRUE 
        AND rules = 'chess'     -- Only games respecting this condition are processed by Stockfish
        AND (LENGTH(initial_setup) = 0 OR initial_setup = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1') -- Classic set-up
        AND LENGTH(pgn) > 0     -- Only games respecting this condition are processed by Stockfish
        AND pgn ~ E'\\d+\\. '   -- find at least 1 matching move number, i.e. digit followed by at dot
)

, cast_types AS (
    SELECT 
        *,
        end_time::DATE                  AS end_time_date,
        TO_CHAR(end_time, 'YYYY-MM')    AS end_time_month
    FROM filter_table    
)

, define_playing AS (
    SELECT 
        *,
        CASE 
            WHEN LOWER(username) = LOWER(white__username) THEN 'White'
            WHEN LOWER(username) = LOWER(black__username) THEN 'Black'
            ELSE NULL END AS playing_as
    FROM cast_types
)

, define_result AS (
    SELECT 
        *,
        CASE
            WHEN playing_as = 'White' THEN white__result
            WHEN playing_as = 'Black' THEN black__result
            ELSE NULL END AS playing_result_detailed,
        CASE
            WHEN playing_as = 'White' THEN white__rating
            WHEN playing_as = 'Black' THEN black__rating
            ELSE NULL END AS playing_rating,
        CASE
            WHEN playing_as = 'White' THEN black__rating
            WHEN playing_as = 'Black' THEN white__rating
            ELSE NULL END AS opponent_rating
    FROM define_playing
)

, define_rating_range AS (
    SELECT
        *,
        CASE
            {% for idx in range(elo_range_values|length) %}
            WHEN playing_rating < {{ elo_range_values[idx] }} THEN
                '{{ "%04d"|format(elo_range_values[idx-1] if idx > 0 else 0) }}-{{ "%04d"|format(elo_range_values[idx]) }}'
            {% endfor %}
            ELSE '{{ "%04d"|format(elo_range_values[-1]) }}+'
        END AS playing_rating_range,
        CASE
            {% for idx in range(elo_range_values|length) %}
            WHEN opponent_rating < {{ elo_range_values[idx] }} THEN
                '{{ "%04d"|format(elo_range_values[idx-1] if idx > 0 else 0) }}-{{ "%04d"|format(elo_range_values[idx]) }}'
            {% endfor %}
            ELSE '{{ "%04d"|format(elo_range_values[-1]) }}+'
        END AS opponent_rating_range
    FROM define_result
)

, simplify_result AS (
    SELECT 
        *,
        CASE    
            WHEN playing_result_detailed IN ('checkmated', 'resigned', 'abandoned', 'timeout')                                      THEN 'Lose'
            WHEN playing_result_detailed IN ('win')                                                                                 THEN 'Win'
            WHEN playing_result_detailed IN ('stalemate', 'repetition', 'agreed', 'timevsinsufficient', 'insufficient', '50move')   THEN 'Draw'
            ELSE NULL END AS playing_result
    FROM define_rating_range
)

SELECT 
    * 
FROM simplify_result