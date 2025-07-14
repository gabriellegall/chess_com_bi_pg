{{ config(
    materialized = 'incremental',
    unique_key = 'uuid',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)"
    ]
) }}

WITH incremental_partition AS (
    SELECT 
        *
    FROM {{ source('chess_com', 'players_games') }} 

    {% if is_incremental() %}
    WHERE uuid NOT IN (SELECT DISTINCT uuid FROM {{ this }})
    {% endif %}
)

, filter_table AS (
    SELECT 
        *
    FROM incremental_partition
    WHERE TRUE 
        AND LENGTH(pgn) > 0 -- Only games respecting this condition are processed by Stockfish
        AND rules = 'chess' -- Only games respecting this condition are processed by Stockfish
        AND (LENGTH(initial_setup) = 0 OR initial_setup = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1') -- Classic set-up
)

, cast_types AS (
    SELECT 
        *
        , end_time::DATE                  AS end_time_date
        , TO_CHAR(end_time, 'YYYY-MM')    AS end_time_month
    FROM filter_table    
)

, define_playing AS (
    SELECT 
        *
        , CASE 
            WHEN LOWER(username) = LOWER(white__username) THEN 'White'
            WHEN LOWER(username) = LOWER(black__username) THEN 'Black'
            ELSE NULL END AS playing_as
    FROM cast_types
)

, define_result AS (
    SELECT 
        *
        , CASE
            WHEN playing_as = 'White' THEN white__result
            WHEN playing_as = 'Black' THEN black__result
            ELSE NULL END AS playing_result_detailed
        , CASE
            WHEN playing_as = 'White' THEN white__rating
            WHEN playing_as = 'Black' THEN black__rating
            ELSE NULL END AS playing_rating
        , CASE
            WHEN playing_as = 'White' THEN black__rating
            WHEN playing_as = 'Black' THEN white__rating
            ELSE NULL END AS opponent_rating
    FROM define_playing
)

, simplify_result AS (
    SELECT 
        *
        , CASE    
            WHEN playing_result_detailed IN ('checkmated', 'resigned', 'abandoned', 'timeout')                                      THEN 'Lose'
            WHEN playing_result_detailed IN ('win')                                                                                 THEN 'Win'
            WHEN playing_result_detailed IN ('stalemate', 'repetition', 'agreed', 'timevsinsufficient', 'insufficient', '50move')   THEN 'Draw'
            ELSE NULL END AS playing_result
    FROM define_result
)

SELECT 
    * 
FROM simplify_result