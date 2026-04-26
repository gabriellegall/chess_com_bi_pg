{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_end_time ON {{ this }} (end_time)"
    ]
) }}

select
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
from {{ ref('int_games_base') }} g
where true
    and {{ games_scope_condition('g') }}
    {% if is_incremental() %}
    and g.end_time > (
        select max(i.end_time)
        from {{ this }} i
    )
    {% endif %}