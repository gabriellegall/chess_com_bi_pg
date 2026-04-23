{{ config(materialized = 'view') }}

select *
from {{ source('openings', 'chess_openings') }}