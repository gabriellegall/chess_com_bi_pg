{{ config(
    materialized = 'view'
) }}

SELECT
    {{ dbt_utils.generate_surrogate_key(['pb.username']) }} AS players_sk,
    pb.username,
    coalesce(pm.username_global, pb.username) AS username_global
FROM {{ ref('int_players_base') }} pb
LEFT JOIN {{ ref('stg_seeds__username_mapping') }} pm
    ON pm.username_normalized = lower(pb.username)