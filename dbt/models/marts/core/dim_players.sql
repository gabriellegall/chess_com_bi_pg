{{ config(
    materialized = 'view'
) }}

select
    {{ dbt_utils.generate_surrogate_key(['pb.username']) }} as players_sk,
    pb.username,
    coalesce(pm.username_global, pb.username) as username_global
from {{ ref('int_players_base') }} pb
left join {{ ref('stg_seeds__username_mapping') }} pm
    on pm.username_normalized = lower(pb.username)