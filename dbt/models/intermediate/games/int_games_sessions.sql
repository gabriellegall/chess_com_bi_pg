{{ config(
    materialized = 'incremental',
    incremental_strategy = 'merge',
    unique_key = ['username', 'uuid'],
    post_hook = [
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_end_time ON {{ this }} (end_time)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_run_timestamp ON {{ this }} (run_timestamp)"
    ]
) }}

{#
    ### Session logic (gaps and islands):
    A new session starts when the previous game of the same [username] ended more than
    [sessions.gap_minutes] before the current game ended.

    ### Incremental strategy (merge on username + uuid):
    For each [username], every game since the start of their last stored session is re-processed and rewritten.
    A new game that continues the last stored session gets the correct ranking, and the session-level window
    functions (e.g. [nb_games_in_session]) are refreshed on the earlier games of that session too.
    Every row written by a run gets that run's [run_timestamp], which drives the downstream incremental models.
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
        LAG(gs.playing_result) OVER w AS prev_playing_result,
        LAG(gs.playing_result, 2) OVER w AS prev_2_playing_result
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
        COUNT(*) OVER s AS nb_games_in_session,
        ROW_NUMBER() OVER (
            PARTITION BY sn.username, sn.session_number
            ORDER BY sn.end_time ASC, sn.uuid ASC
        ) AS session_game_rank,
        CASE
            WHEN sn.is_new_session = 0 THEN sn.prev_playing_result
        END AS previous_game_result_in_session,
        sn.prev_playing_result,
        sn.prev_2_playing_result
    FROM session_numbers AS sn
    WINDOW s AS (PARTITION BY sn.username, sn.session_number)
)

SELECT
    sa.username,
    sa.uuid,
    sa.end_time,
    sa.session_start_time,
    sa.nb_games_in_session,
    sa.session_game_rank,
    sa.previous_game_result_in_session,
    -- Tilt flags: only previous games of the same session count (NULL when not enough of them)
    CASE
        WHEN sa.session_game_rank >= 2
            THEN sa.prev_playing_result = 'Lose'
    END AS is_last_1_game_loss,
    CASE
        WHEN sa.session_game_rank >= 3
            THEN sa.prev_playing_result = 'Lose' AND sa.prev_2_playing_result = 'Lose'
    END AS is_last_2_games_loss,
    CURRENT_TIMESTAMP AS run_timestamp
FROM session_attributes AS sa
