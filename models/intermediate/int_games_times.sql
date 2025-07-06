{{ config(
    materialized = 'incremental',
    unique_key = ['uuid','move_number'],
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)"
    ]
) }}

SELECT 
    *
FROM {{ source('times', 'players_games_times') }}

{% if is_incremental() %}
WHERE uuid NOT IN (SELECT DISTINCT uuid FROM {{ this }})
{% endif %}