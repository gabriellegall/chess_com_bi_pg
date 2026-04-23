{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_end_time ON {{ this }} (end_time)"
    ]
) }}

SELECT
    g.*
FROM {{ ref('int_games') }} g
WHERE TRUE
    AND g.end_time >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '{{ var('data_scope')['month_history_depth'] }} months')
    AND g.time_class = ANY(ARRAY{{ var('data_scope')['time_class'] }}::text[])
    AND g.rated
    {% if is_incremental() %}
    AND NOT EXISTS (
        SELECT 1
        FROM {{ this }} i
        WHERE i.uuid = g.uuid
    )
    {% endif %}
