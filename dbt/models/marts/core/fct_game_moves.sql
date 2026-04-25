{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

SELECT
  {{ dbt_utils.generate_surrogate_key(['gm.username']) }} as players_sk,
  {{ dbt_utils.generate_surrogate_key(['gm.uuid', 'gm.username']) }} as games_sk,
  gm.*
FROM {{ ref('int_game_moves_enriched') }} gm
{% if is_incremental() %}
WHERE gm.log_timestamp > (
  SELECT MAX(i.log_timestamp)
  FROM {{ this }} i
)
{% endif %}