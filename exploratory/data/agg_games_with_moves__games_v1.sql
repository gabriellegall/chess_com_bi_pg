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
        nb_massive_blunder_early_playing,
        nb_massive_blunder_mid_playing,
        nb_massive_blunder_late_playing,
        nb_massive_blunder_very_late_playing,
        -- Throw
        nb_throw_playing,
        nb_throw_blunder_playing,
        nb_throw_massive_blunder_playing,
        nb_throw_blunder_opponent,
        nb_throw_massive_blunder_opponent,
        -- Missed opp.
        nb_missed_opportunity_playing,
        nb_missed_opportunity_blunder_playing,
        nb_missed_opportunity_massive_blunder_playing,
        nb_missed_opportunity_opponent,
        nb_missed_opportunity_blunder_opponent,
        nb_missed_opportunity_massive_blunder_opponent,
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
    AND playing_result          IN ('Win', 'Lose')
    AND playing_as = 'White'
