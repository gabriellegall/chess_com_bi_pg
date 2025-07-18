{{ config(
    materialized = 'view'
) }}

SELECT 
    *,
    (COUNT(*) OVER (
        PARTITION BY username, time_class, end_time_month, opponent_rating_range, game_phase_key
    ) > {{ var('datamart')['min_games_played'] }}) AS has_enough_games
FROM {{ ref('dwh_agg_games_with_moves__prep') }}