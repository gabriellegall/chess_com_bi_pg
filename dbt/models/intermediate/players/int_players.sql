{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_username ON {{ this }} (username)"
    ]
) }}

with distinct_players as (
    select distinct
        g.username
    from {{ ref('int_games_filtered') }} g
)

select
    p.username,
    coalesce(username_mapping.target_username, p.username) as username_global
from distinct_players p
left join {{ ref('username_mapping') }} username_mapping
    on lower(username_mapping.username) = lower(p.username)
{% if is_incremental() %}
where not exists (
    select 1
    from {{ this }} i
    where i.username = p.username
)
{% endif %}