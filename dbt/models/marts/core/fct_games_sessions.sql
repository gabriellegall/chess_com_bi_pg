{{ config(
    materialized = 'incremental',
    incremental_strategy = 'merge',
    unique_key = 'games_sk',
    post_hook = [
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_run_timestamp ON {{ this }} (run_timestamp)"
    ]
) }}

{#
    One row per game and player with the session it belongs to (see int_games_sessions).
    Incremental merge on games_sk: the rows int_games_sessions (re)wrote since the last run (run_timestamp),
    i.e. the new games and the earlier games of the sessions they continue.
#}

SELECT
    {{ dbt_utils.generate_surrogate_key(['s.username']) }} AS players_sk,
    {{ dbt_utils.generate_surrogate_key(['s.uuid', 's.username']) }} AS games_sk,
    {{ dbt_utils.generate_surrogate_key(['s.username', 's.session_start_time']) }} AS sessions_sk,
    s.username,
    s.uuid,
    s.end_time,
    s.session_start_time,
    s.nb_games_in_session,
    s.session_game_rank,
    s.previous_game_result_in_session,
    s.is_last_1_game_loss,
    s.is_last_2_games_loss,
    s.run_timestamp
FROM {{ ref('int_games_sessions') }} AS s
{% if is_incremental() %}
    WHERE s.run_timestamp > (
        SELECT MAX(i.run_timestamp)
        FROM {{ this }} AS i
    )
{% endif %}
