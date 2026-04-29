{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

SELECT
    pgt.uuid,
    pgt.move_number,
    pgt.time_remaining_seconds,
    pgt.time_remaining,
    pgt.log_timestamp
FROM {{ ref('stg_times__players_games_times') }} pgt
{% if is_incremental() %}
    WHERE pgt.log_timestamp > (
        SELECT MAX(i.log_timestamp)
        FROM {{ this }} i
    )
{% endif %}