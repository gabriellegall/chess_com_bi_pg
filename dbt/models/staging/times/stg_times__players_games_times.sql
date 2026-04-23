{{ config(materialized = 'view') }}

select *
from {{ source('times', 'players_games_times') }}