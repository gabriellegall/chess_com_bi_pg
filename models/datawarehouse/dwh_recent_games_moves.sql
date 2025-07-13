{{ config(
    materialized='materialized_view'
  ) 
}}

WITH define_expected_moves AS (
    SELECT  
        uuid,
        username,
        MAX(time_class) AS time_class,
        MAX(playing_result) AS playing_result,
        MAX(opponent_rating_range) AS opponent_rating_range,
        MAX(url) AS url,
        MAX(end_time) AS end_time,
        MAX(playing_as) AS playing_as
    FROM {{ ref('dwh_games_with_moves') }}
    WHERE 
        end_time_date >= DATE_TRUNC('week', CURRENT_DATE - INTERVAL '7 days')
    GROUP BY uuid, username
),

expected_move_numbers AS (
    SELECT generate_series(1, 60, 5) AS move_number
),

expanded_moves AS (
    SELECT 
        d.uuid,
        d.username,
        d.time_class,
        d.playing_result,
        d.opponent_rating_range,
        d.url,
        d.end_time,
        d.playing_as,
        e.move_number
    FROM define_expected_moves d
    CROSS JOIN expected_move_numbers e
),

joined_moves AS (
    SELECT 
        em.*,
        gm.score_playing
    FROM expanded_moves em
    LEFT JOIN {{ ref('dwh_games_with_moves') }} gm
      ON gm.username = em.username
      AND gm.uuid = em.uuid
      AND gm.move_number = em.move_number
)

SELECT 
    uuid,
    username,
    time_class,
    playing_result,
    opponent_rating_range,
    url,
    end_time,
    playing_as,
    move_number,
    COALESCE(
        score_playing,
        LAST_VALUE(score_playing) OVER (
            PARTITION BY uuid, username 
            ORDER BY move_number 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )
    ) AS score_playing
FROM joined_moves
ORDER BY end_time DESC