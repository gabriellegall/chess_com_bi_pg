{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
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
select
    {{ dbt_utils.generate_surrogate_key(['username']) }} as players_sk,
    {{ dbt_utils.generate_surrogate_key(['uuid', 'username']) }} as games_sk,
    *
from incremental_partition