{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

{% set openings_depth = var('openings')['hierarchy_depth'] + 1 %}

SELECT
    {{ dbt_utils.generate_surrogate_key(['igo.username']) }} as players_sk,
    {{ dbt_utils.generate_surrogate_key(['igo.uuid', 'igo.username']) }} as games_sk,
    igo.username,
    igo.uuid,
    {% for n in range(1, openings_depth) %}
        igo.opener_{{ n }}_moves,
        igo.uci_hierarchy_level_{{ n }}_name,
    {% endfor %}
    igo.log_timestamp
FROM {{ ref('int_games_openings') }} igo
{% if is_incremental() %}
WHERE igo.log_timestamp > (
    SELECT MAX(i.log_timestamp)
    FROM {{ this }} i
)
{% endif %}
