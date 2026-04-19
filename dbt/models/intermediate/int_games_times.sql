{{ config(
    materialized = 'incremental',
    unique_key = ['uuid','move_number'],
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

SELECT 
    pgt.*
FROM {{ source('times', 'players_games_times') }} pgt

{% if is_incremental() %}
WHERE pgt.log_timestamp > (
    SELECT MAX(i.log_timestamp)
    FROM {{ this }} i
)
{% endif %}