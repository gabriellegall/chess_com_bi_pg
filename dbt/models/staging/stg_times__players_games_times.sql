{{ config(materialized='view') }}

SELECT
  *
FROM {{ source('times', 'players_games_times') }}
