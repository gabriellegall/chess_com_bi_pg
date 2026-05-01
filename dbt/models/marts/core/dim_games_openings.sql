{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook = [
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

{% set openings_depth = var('openings')['hierarchy_depth'] + 1 %}

SELECT
    {{ dbt_utils.generate_surrogate_key(['gop.username']) }} AS players_sk,
    {{ dbt_utils.generate_surrogate_key(['gop.uuid', 'gop.username']) }} AS games_sk,
    gop.username,
    gop.uuid,
    {% for n in range(1, openings_depth) %}
        gop.opener_{{ n }}_moves,
        gop.uci_hierarchy_level_{{ n }}_name,
    {% endfor %}
    gop.log_timestamp
FROM {{ ref('int_games_openings') }} gop
{% if is_incremental() %}
    WHERE gop.log_timestamp > (
        SELECT MAX(i.log_timestamp)
        FROM {{ this }} i
    )
{% endif %}
