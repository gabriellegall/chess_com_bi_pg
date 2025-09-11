SELECT 
    *
FROM dwh.dwh_agg_games_with_moves
WHERE TRUE
    AND aggregation_level       = 'Games'
    AND playing_rating_range    = opponent_rating_range
    -- AND playing_rating_range    = '0800-1000'
    AND playing_result IN ('Win', 'Lose')
    AND username = 'Zundorn'
    -- AND end_time >= '2025-05-01'
    AND playing_as = 'White'
    -- AND time_control = '600'
