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
    opener_2_moves,
    opener_4_moves,
    opener_6_moves,
    -- Time management
    prct_time_remaining_playing_early,
    prct_time_remaining_playing_mid,
    prct_time_remaining_playing_late,
    -- Mistakes
        -- Massive blunders
        nb_massive_blunder_playing,
        -- Throw (Binary)
        CASE WHEN nb_throw_blunder_playing > 0 THEN 1 ELSE 0 END                            AS nb_throw_blunder_playing,
        CASE WHEN nb_throw_massive_blunder_playing> 0 THEN 1 ELSE 0 END                     AS nb_throw_massive_blunder_playing,
        CASE WHEN nb_throw_massive_blunder_playing_early > 0 THEN 1 ELSE 0 END              AS nb_throw_massive_blunder_playing_early,
        CASE WHEN nb_throw_massive_blunder_playing_mid > 0 THEN 1 ELSE 0 END                AS nb_throw_massive_blunder_playing_mid,
        CASE WHEN nb_throw_massive_blunder_playing_late > 0 THEN 1 ELSE 0 END               AS nb_throw_massive_blunder_playing_late,
        CASE WHEN nb_throw_blunder_playing_early > 0 THEN 1 ELSE 0 END                      AS nb_throw_blunder_playing_early,
        CASE WHEN nb_throw_blunder_playing_mid > 0 THEN 1 ELSE 0 END                        AS nb_throw_blunder_playing_mid,
        CASE WHEN nb_throw_blunder_playing_late > 0 THEN 1 ELSE 0 END                       AS nb_throw_blunder_playing_late,
        -- Missed opp. (Binary)
        CASE WHEN nb_missed_opportunity_blunder_playing > 0 THEN 1 ELSE 0 END               AS nb_missed_opportunity_blunder_playing,
        CASE WHEN nb_missed_opportunity_massive_blunder_playing > 0 THEN 1 ELSE 0 END       AS nb_missed_opportunity_massive_blunder_playing,
        CASE WHEN nb_missed_opportunity_massive_blunder_playing_early > 0 THEN 1 ELSE 0 END AS nb_missed_opportunity_massive_blunder_playing_early,
        CASE WHEN nb_missed_opportunity_massive_blunder_playing_mid > 0 THEN 1 ELSE 0 END   AS nb_missed_opportunity_massive_blunder_playing_mid,
        CASE WHEN nb_missed_opportunity_massive_blunder_playing_late > 0 THEN 1 ELSE 0 END  AS nb_missed_opportunity_massive_blunder_playing_late,
        CASE WHEN nb_missed_opportunity_blunder_playing_early > 0 THEN 1 ELSE 0 END         AS nb_missed_opportunity_blunder_playing_early,
        CASE WHEN nb_missed_opportunity_blunder_playing_mid > 0 THEN 1 ELSE 0 END           AS nb_missed_opportunity_blunder_playing_mid,
        CASE WHEN nb_missed_opportunity_blunder_playing_late > 0 THEN 1 ELSE 0 END          AS nb_missed_opportunity_blunder_playing_late,
        -- Time pressure
        first_blunder_playing_prct_time_remaining,
        first_massive_blunder_playing_prct_time_remaining,
        first_missed_opp_massive_blunder_playing_prct_time_remaining,
        first_throw_massive_blunder_playing_prct_time_remaining    
FROM dwh.dwh_agg_games_with_moves
WHERE TRUE
    AND aggregation_level       = 'Games'
    AND playing_rating_range    = opponent_rating_range
    AND playing_result IN ('Win', 'Lose')
    -- AND username = 'Zundorn'
    -- AND time_control = '300+5'
    -- AND playing_rating_range = '0800-1000'