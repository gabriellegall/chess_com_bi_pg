{{ config(
    materialized = 'view'
) }}

SELECT 
    *
FROM {{ source('openings', 'chess_openings') }}