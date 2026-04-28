{{ config(
    materialized = 'incremental',
    incremental_strategy = 'merge',
    unique_key = 'username',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

SELECT
    g.username,
    max(g.log_timestamp) AS log_timestamp
FROM {{ ref('int_games_filtered') }} g
WHERE
    TRUE
    {% if is_incremental() %}
        AND g.log_timestamp > (
            SELECT max(i.log_timestamp)
            FROM {{ this }} i
        )
    {% endif %}
GROUP BY g.username