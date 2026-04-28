{{ config(
    materialized = 'view'
) }}

SELECT
    username,
    lower(username) AS username_normalized,
    target_username AS username_global
FROM {{ ref('username_mapping') }}