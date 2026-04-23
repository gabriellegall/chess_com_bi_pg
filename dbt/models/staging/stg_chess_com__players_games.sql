{{ config(materialized='view') }}

SELECT
  *
FROM {{ source('chess_com', 'players_games') }}
