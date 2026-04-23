{{ config(materialized = 'view') }}

select *
from {{ source('stockfish', 'players_games_moves') }}