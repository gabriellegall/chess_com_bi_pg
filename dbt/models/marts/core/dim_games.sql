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
    end_time,
    url,
    pgn,
    time_control,
    rated,
    tcn,
    uuid,
    initial_setup,
    fen,
    time_class,
    rules,
    white__rating,
    white__result,
    white__aid,
    white__username,
    white__uuid,
    black__rating,
    black__result,
    black__aid,
    black__username,
    black__uuid,
    eco,
    username,
    archive_url,
    log_timestamp,
    accuracies__white,
    accuracies__black,
    start_time,
    tournament,
    end_time_date,
    end_time_month,
    playing_as,
    playing_result_detailed,
    playing_rating,
    opponent_rating,
    playing_rating_range,
    opponent_rating_range,
    playing_result
FROM {{ ref('int_games_filtered') }} AS g
WHERE
    TRUE
    {% if is_incremental() %}
        AND end_time > (
            SELECT MAX(i.end_time)
            FROM {{ this }} AS i
        )
    {% endif %}