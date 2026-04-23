{{ config(materialized='view') }}

SELECT
  *
FROM {{ source('stockfish', 'players_games_moves') }}
