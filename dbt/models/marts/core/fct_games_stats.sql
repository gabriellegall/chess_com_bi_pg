{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

SELECT
    {{ dbt_utils.generate_surrogate_key(['igs.username']) }} as players_sk,
    {{ dbt_utils.generate_surrogate_key(['igs.uuid', 'igs.username']) }} as games_sk,
    igs.*
FROM {{ ref('int_games_stats') }} igs
{% if is_incremental() %}
WHERE igs.log_timestamp > (
    SELECT MAX(i.log_timestamp)
    FROM {{ this }} i
)
{% endif %}