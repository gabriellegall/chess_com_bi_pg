{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_end_time ON {{ this }} (end_time)"
    ]
) }}

WITH incremental_partition AS (
    SELECT 
        g.*
    FROM {{ ref('int_games_filtered') }} g

    {% if is_incremental() %}
    WHERE g.end_time > (
        SELECT MAX(i.end_time)
        FROM {{ this }} i
    )
    {% endif %}
)

SELECT * FROM incremental_partition