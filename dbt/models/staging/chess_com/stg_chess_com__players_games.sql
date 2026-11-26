{{ config(materialized = 'view') }}

{#
    ### Rating deltas:
    chess.com stores the post-game rating in each game, so the pre-game rating is the rating of the previous
    rated game of the same [username], [rules] and [time_class] (each one has its own rating pool).
    It is computed on the whole source BEFORE [processable_games_condition] is applied: filtered-out rated games
    (e.g. no clock data) still moved the rating. As this model is a view, the window always sees the full history,
    so the downstream incremental models need no lookback logic.
#}

WITH source_data AS (
    SELECT *
    FROM {{ source('chess_com', 'players_games') }}
)

, cast_types AS (
    SELECT
        *,
        end_time::date AS end_time_date,
        TO_CHAR(end_time, 'YYYY-MM') AS end_time_month
    FROM source_data
)

, define_playing AS (
    SELECT
        *,
        CASE
            WHEN LOWER(username) = LOWER(white__username) THEN 'White'
            WHEN LOWER(username) = LOWER(black__username) THEN 'Black'
            ELSE NULL
        END AS playing_as
    FROM cast_types
)

, define_result AS (
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

, define_prev_rating AS (
    SELECT
        *,
        CASE
            WHEN rated THEN
                LAG(playing_rating) OVER (
                    PARTITION BY username, rules, time_class, rated
                    ORDER BY end_time ASC, uuid ASC
                )
        END AS prev_playing_rating
    FROM define_result
)

, define_rating_delta AS (
    SELECT
        *,
        playing_rating - prev_playing_rating AS playing_rating_delta,
        -- Zero-sum estimate: exact under Elo, approximate under Glicko when both players' RDs differ
        opponent_rating + (playing_rating - prev_playing_rating) AS opponent_prev_rating_estimated
    FROM define_prev_rating
)

, filter_table AS (
    SELECT *
    FROM define_rating_delta AS game
    WHERE
        TRUE
        AND {{ var('processable_games_condition') }}
)

SELECT *
FROM filter_table
