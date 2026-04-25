{{ config(
    materialized = 'incremental',
    incremental_strategy = 'merge',
    unique_key = 'username',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_username ON {{ this }} (username)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_log_timestamp ON {{ this }} (log_timestamp)"
    ]
) }}

select
    g.username,
    max(g.log_timestamp) as log_timestamp
from {{ ref('int_games_filtered') }} g
where true
{% if is_incremental() %}
  and g.log_timestamp > (
      select max(i.log_timestamp)
      from {{ this }} i
  )
{% endif %}
group by g.username