{{ config(materialized = 'view') }}

SELECT
    username,
    LOWER(username) AS username_normalized,
    target_username AS username_global
FROM {{ ref('username_mapping') }}