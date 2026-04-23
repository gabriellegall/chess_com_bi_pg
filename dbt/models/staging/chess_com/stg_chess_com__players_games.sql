{{ config(materialized = 'view') }}

select *
from {{ source('chess_com', 'players_games') }}