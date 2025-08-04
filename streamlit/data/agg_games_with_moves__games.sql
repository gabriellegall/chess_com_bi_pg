SELECT 
    username, 
    nb_moves,
    time_class,
    time_control,
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
        CASE WHEN nb_throw_blunder_playing > 0 THEN 1 ELSE 0 END AS nb_throw_blunder_playing,
        CASE WHEN nb_throw_massive_blunder_playing> 0 THEN 1 ELSE 0 END AS nb_throw_massive_blunder_playing,
        CASE WHEN nb_throw_massive_blunder_playing_early > 0 THEN 1 ELSE 0 END AS   nb_throw_massive_blunder_playing_early,
        CASE WHEN nb_throw_massive_blunder_playing_mid > 0 THEN 1 ELSE 0 END AS     nb_throw_massive_blunder_playing_mid,
        CASE WHEN nb_throw_massive_blunder_playing_late > 0 THEN 1 ELSE 0 END AS    nb_throw_massive_blunder_playing_late,
        CASE WHEN nb_throw_blunder_playing_early > 0 THEN 1 ELSE 0 END AS   nb_throw_blunder_playing_early,
        CASE WHEN nb_throw_blunder_playing_mid > 0 THEN 1 ELSE 0 END AS     nb_throw_blunder_playing_mid,
        CASE WHEN nb_throw_blunder_playing_late > 0 THEN 1 ELSE 0 END AS    nb_throw_blunder_playing_late,
        -- Missed opp.
        CASE WHEN nb_missed_opportunity_blunder_playing > 0 THEN 1 ELSE 0 END AS nb_missed_opportunity_blunder_playing,
        CASE WHEN nb_missed_opportunity_massive_blunder_playing > 0 THEN 1 ELSE 0 END AS nb_missed_opportunity_massive_blunder_playing,
        CASE WHEN nb_missed_opportunity_massive_blunder_playing_early > 0 THEN 1 ELSE 0 END AS nb_missed_opportunity_massive_blunder_playing_early,
        CASE WHEN nb_missed_opportunity_massive_blunder_playing_mid > 0 THEN 1 ELSE 0 END   AS nb_missed_opportunity_massive_blunder_playing_mid,
        CASE WHEN nb_missed_opportunity_massive_blunder_playing_late > 0 THEN 1 ELSE 0 END  AS nb_missed_opportunity_massive_blunder_playing_late,
        CASE WHEN nb_missed_opportunity_blunder_playing_early > 0 THEN 1 ELSE 0 END AS nb_missed_opportunity_blunder_playing_early,
        CASE WHEN nb_missed_opportunity_blunder_playing_mid > 0 THEN 1 ELSE 0 END   AS nb_missed_opportunity_blunder_playing_mid,
        CASE WHEN nb_missed_opportunity_blunder_playing_late > 0 THEN 1 ELSE 0 END  AS nb_missed_opportunity_blunder_playing_late,
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
