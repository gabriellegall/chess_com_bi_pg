{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_uuid ON {{ this }} (uuid)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

SELECT
  gm.*
FROM {{ ref('int_games_with_moves_enriched') }} gm
{% if is_incremental() %}
WHERE gm.log_timestamp > (
  SELECT MAX(i.log_timestamp)
  FROM {{ this }} i
)
{% endif %}