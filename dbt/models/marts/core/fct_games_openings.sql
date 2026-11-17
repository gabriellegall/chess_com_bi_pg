{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook = [
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_run_timestamp ON {{ this }} (run_timestamp)"
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
    gop.run_timestamp
FROM {{ ref('int_games_openings') }} gop
{% if is_incremental() %}
    WHERE gop.run_timestamp > (
        SELECT MAX(i.run_timestamp)
        FROM {{ this }} i
    )
{% endif %}
