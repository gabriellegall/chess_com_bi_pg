{{ config(
    materialized = 'view'
) }}

select
    username,
    lower(username) as username_normalized,
    target_username as username_global
from {{ ref('username_mapping') }}