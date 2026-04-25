{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_players_sk ON {{ this }} (players_sk)",
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_username ON {{ this }} (username)"
    ]
) }}

select
    {{ dbt_utils.generate_surrogate_key(['p.username']) }} as players_sk,
    p.username,
    p.username_global
from {{ ref('int_players') }} p
{% if is_incremental() %}
where not exists (
    select 1
    from {{ this }} i
    where i.username = p.username
)
{% endif %}