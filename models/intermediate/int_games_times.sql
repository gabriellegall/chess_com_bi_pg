{{ config(
    materialized = 'incremental',
    unique_key = ['uuid','move_number'],
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)"
    ]
) }}

SELECT 
    *
FROM {{ source('times', 'games_times') }}

{% if is_incremental() %}
WHERE log_timestamp > (SELECT MAX(log_timestamp) FROM {{ this }})
{% endif %}