{{ config(
    materialized = 'incremental',
    unique_key = ['uuid','move_number'],
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)"
    ]
) }}

SELECT 
    pgt.*
FROM {{ source('times', 'players_games_times') }} pgt

{% if is_incremental() %}
WHERE NOT EXISTS (
    SELECT 1
    FROM {{ this }} i
    WHERE i.uuid = pgt.uuid
)
{% endif %}