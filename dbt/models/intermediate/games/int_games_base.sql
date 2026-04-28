{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_end_time ON {{ this }} (end_time)"
    ]
) }}

{% set elo_range_values = var('elo_range') %}

WITH incremental_partition AS (
    SELECT 
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
    FROM {{ ref('stg_chess_com__players_games') }} pg
    {% if is_incremental() %}
        WHERE pg.end_time > (
                SELECT max(i.end_time)
                FROM {{ this }} i
        )
    {% endif %}
),

define_rating_range AS (
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
    FROM incremental_partition
),

simplify_result AS (
    SELECT 
        *,
        CASE    
            WHEN playing_result_detailed IN ('checkmated', 'resigned', 'abandoned', 'timeout')                                      THEN 'Lose'
            WHEN playing_result_detailed IN ('win')                                                                                 THEN 'Win'
            WHEN playing_result_detailed IN ('stalemate', 'repetition', 'agreed', 'timevsinsufficient', 'insufficient', '50move')   THEN 'Draw'
            ELSE null END AS playing_result
    FROM define_rating_range
)

SELECT 
    * 
FROM simplify_result