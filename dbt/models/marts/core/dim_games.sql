{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook = [
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_end_time ON {{ this }} (end_time)"
    ]
) }}

SELECT
    {{ dbt_utils.generate_surrogate_key(['username']) }} AS players_sk,
    {{ dbt_utils.generate_surrogate_key(['uuid', 'username']) }} AS games_sk,
    g.end_time,
    g.url,
    g.pgn,
    g.time_control,
    g.rated,
    g.tcn,
    g.uuid,
    g.initial_setup,
    g.fen,
    g.time_class,
    g.rules,
    g.white__rating,
    g.white__result,
    g.white__aid,
    g.white__username,
    g.white__uuid,
    g.black__rating,
    g.black__result,
    g.black__aid,
    g.black__username,
    g.black__uuid,
    g.eco,
    g.username,
    g.archive_url,
    g.log_timestamp,
    g.accuracies__white,
    g.accuracies__black,
    g.start_time,
    g.tournament,
    g.end_time_date,
    g.end_time_month,
    g.playing_as,
    g.playing_result_detailed,
    g.playing_rating,
    g.opponent_rating,
    g.playing_rating_range,
    g.opponent_rating_range,
    g.playing_result
FROM {{ ref('int_games_filtered') }} g
WHERE
    TRUE
    {% if is_incremental() %}
        AND g.end_time > (
            SELECT MAX(i.end_time)
            FROM {{ this }} i
        )
    {% endif %}