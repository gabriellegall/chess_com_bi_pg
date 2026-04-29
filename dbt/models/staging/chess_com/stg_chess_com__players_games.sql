{{ config(materialized = 'view') }}

WITH source_data AS (
    SELECT *
    FROM {{ source('chess_com', 'players_games') }}
),

filter_table AS (
    SELECT *
    FROM source_data
    WHERE
        TRUE
        AND rules = 'chess'
        AND (
            LENGTH(initial_setup) = 0
            OR initial_setup = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        )
        AND LENGTH(pgn) > 0
        AND pgn ~ E'\\d+\\. '
),

cast_types AS (
    SELECT
        *,
        end_time::date AS end_time_date,
        TO_CHAR(end_time, 'YYYY-MM') AS end_time_month
    FROM filter_table
),

define_playing AS (
    SELECT
        *,
        CASE
            WHEN LOWER(username) = LOWER(white__username) THEN 'White'
            WHEN LOWER(username) = LOWER(black__username) THEN 'Black'
            ELSE NULL
        END AS playing_as
    FROM cast_types
),

define_result AS (
    SELECT
        *,
        CASE
            WHEN playing_as = 'White' THEN white__result
            WHEN playing_as = 'Black' THEN black__result
            ELSE NULL
        END AS playing_result_detailed,
        CASE
            WHEN playing_as = 'White' THEN white__rating
            WHEN playing_as = 'Black' THEN black__rating
            ELSE NULL
        END AS playing_rating,
        CASE
            WHEN playing_as = 'White' THEN black__rating
            WHEN playing_as = 'Black' THEN white__rating
            ELSE NULL
        END AS opponent_rating
    FROM define_playing
)

SELECT *
FROM define_result