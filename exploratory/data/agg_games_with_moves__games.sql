SELECT 
    username, 
    time_class,
    end_time,
    playing_as,
    playing_rating_range,
    opponent_rating_range,
    playing_result,
    prct_time_remaining_early,
    prct_time_remaining_mid,
    prct_time_remaining_late,
    -- Mistakes
    nb_massive_blunder_playing,
    nb_blunder_playing - nb_massive_blunder_playing AS nb_blunder_playing,
    -- Mistakes under time pressure
    first_blunder_playing_prct_time_remaining,
    first_massive_blunder_playing_prct_time_remaining  
FROM dwh.dwh_agg_games_with_moves__prep
WHERE TRUE
    AND aggregation_level       = 'Games'
    AND time_class              = 'blitz'
    AND time_control            = '300+5'
    AND playing_rating_range    = opponent_rating_range
    AND playing_result IN ('Win', 'Lose')
    AND playing_as              = 'White'