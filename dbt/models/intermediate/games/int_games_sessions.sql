{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook = [
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_end_time ON {{ this }} (end_time)"
    ]
) }}

{#
    ### Session logic (gaps and islands):
    A new session starts when the previous game of the same [username] ended more than
    [sessions.gap_minutes] before the current game ended.

    ### Incremental strategy:
    For each [username], the games since the start of their last stored session are re-read for context.
    However, only new games are written to the table.
    This way, a new game that continues the last stored session gets the correct ranking.
#}

{% set gap_minutes = var('sessions')['gap_minutes'] %}

WITH last_sessions AS (
    {% if is_incremental() %}
        SELECT
            i.username,
            MAX(i.session_start_time) AS last_session_start_time
        FROM {{ this }} AS i
        GROUP BY i.username
    {% else %}
        SELECT
            NULL::TEXT AS username,
            NULL::TIMESTAMPTZ AS last_session_start_time
        WHERE FALSE
    {% endif %}
)

, games_scope AS (
    SELECT
        g.username,
        g.uuid,
        g.end_time,
        g.playing_result
    FROM {{ ref('int_games_filtered') }} AS g
    LEFT JOIN last_sessions AS ls
        ON ls.username = g.username
    -- Context: each username's games since the start of their last stored session
    WHERE g.end_time >= COALESCE(ls.last_session_start_time, '-infinity'::TIMESTAMPTZ)
)

, previous_game AS (
    SELECT
        gs.username,
        gs.uuid,
        gs.end_time,
        LAG(gs.end_time) OVER w AS prev_end_time,
        LAG(gs.playing_result) OVER w AS prev_playing_result
    FROM games_scope AS gs
    WINDOW w AS (PARTITION BY gs.username ORDER BY gs.end_time ASC, gs.uuid ASC)
)

, session_flags AS (
    SELECT
        pg.*,
        CASE
            WHEN pg.prev_end_time IS NULL THEN 1
            WHEN pg.end_time - pg.prev_end_time > INTERVAL '{{ gap_minutes }} minutes' THEN 1
            ELSE 0
        END AS is_new_session
    FROM previous_game AS pg
)

-- Island id: only meaningful within the games scope of this run (never stored)
, session_numbers AS (
    SELECT
        sf.*,
        SUM(sf.is_new_session) OVER (
            PARTITION BY sf.username
            ORDER BY sf.end_time ASC, sf.uuid ASC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS session_number
    FROM session_flags AS sf
)

, session_attributes AS (
    SELECT
        sn.username,
        sn.uuid,
        sn.end_time,
        MIN(sn.end_time) OVER s AS session_start_time,
        ROW_NUMBER() OVER (
            PARTITION BY sn.username, sn.session_number
            ORDER BY sn.end_time ASC, sn.uuid ASC
        ) AS session_game_rank,
        CASE
            WHEN sn.is_new_session = 0 THEN sn.prev_playing_result
        END AS previous_game_result_in_session
    FROM session_numbers AS sn
    WINDOW s AS (PARTITION BY sn.username, sn.session_number)
)

SELECT
    sa.username,
    sa.uuid,
    sa.end_time,
    sa.session_start_time,
    sa.session_game_rank,
    sa.previous_game_result_in_session
FROM session_attributes AS sa
{% if is_incremental() %}
    WHERE sa.end_time > (
        SELECT MAX(i.end_time)
        FROM {{ this }} AS i
    )
{% endif %}
