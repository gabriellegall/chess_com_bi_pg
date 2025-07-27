SELECT 
    username, 
    time_class,
    end_time,
    playing_as,
    playing_rating_range,
    opponent_rating_range,
    playing_result,
    -- Time management
    prct_time_remaining_early,
    prct_time_remaining_mid,
    prct_time_remaining_late,
    -- Mistakes
        -- Massive blunders
        nb_massive_blunder_playing,
        -- Throw
        nb_throw_playing,
        nb_throw_blunder_playing,
        nb_throw_massive_blunder_playing,
        -- Missed opp.
        nb_missed_opportunity_blunder_playing,
        nb_missed_opportunity_massive_blunder_playing,
        -- Standard deviation
        std_score_playing,
        -- Time pressure
        first_blunder_playing_prct_time_remaining,
        first_massive_blunder_playing_prct_time_remaining  
        
FROM dwh.dwh_agg_games_with_moves__prep
WHERE TRUE
    AND aggregation_level       = 'Games'
    AND time_class              = 'blitz'
    AND time_control            = '300+5'
    AND playing_rating_range    = opponent_rating_range
    AND playing_result IN ('Win', 'Lose')
