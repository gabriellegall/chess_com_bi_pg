{{ config(
    materialized = 'incremental',
    unique_key = ['uuid','username','move_number'],
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_username ON {{ this }} (username)",
        "DELETE FROM {{ this }} WHERE end_time::date < DATE_TRUNC('week', CURRENT_DATE - INTERVAL '7 days')"
    ]
) }}

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
        {% if is_incremental() %}
        AND uuid NOT IN (SELECT DISTINCT uuid FROM {{ this }})
        {% endif %}
    GROUP BY uuid, username
)

, expected_move_numbers AS (
    SELECT 1 AS move_number
    UNION ALL
    SELECT generate_series(5, 60, 5) AS move_number
)

, expanded_moves AS (
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
)

, joined_moves AS (
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
        jm.score_playing,
        -- Postgres equivalent of LAST_VALUE IGNORE NULLS:
        (
            SELECT s2.score_playing
            FROM joined_moves s2
            WHERE s2.uuid = jm.uuid
              AND s2.username = jm.username
              AND s2.move_number <= jm.move_number
              AND s2.score_playing IS NOT NULL
            ORDER BY s2.move_number DESC
            LIMIT 1
        )
    ) AS score_playing
FROM joined_moves jm
ORDER BY end_time DESC