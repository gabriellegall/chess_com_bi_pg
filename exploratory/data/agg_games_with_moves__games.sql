SELECT 
    username, 
    time_class,
    end_time,
    playing_rating_range,
    opponent_rating_range,
    CASE WHEN playing_result = 'Win' THEN 1 ELSE 0 END AS playing_result,
    -- Mistakes
    nb_massive_blunder_playing,
    nb_blunder_playing - nb_massive_blunder_playing AS nb_blunder_playing,
    -- Mistakes under time pressure
    first_blunder_playing_prct_time_remaining,
    first_massive_blunder_playing_prct_time_remaining  
FROM dwh.dwh_agg_games_with_moves__prep
WHERE TRUE
    AND aggregation_level = 'Games'
    AND playing_rating_range = opponent_rating_range
    AND time_class = 'blitz'
    AND end_time > '2025-01-01'