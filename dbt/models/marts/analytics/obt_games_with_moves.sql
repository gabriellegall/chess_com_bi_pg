SELECT 
    games_stats.username,
    games_stats.uuid, 
    -- Game info
    games_info.url,
    games_info.eco,
    games_info.end_time,
    games_info.time_class,
    games_info.time_control,
    games_info.playing_as,
    games_info.playing_rating,
    games_info.playing_rating_range,
    games_info.opponent_rating,
    games_info.opponent_rating_range,
    games_info.playing_result,
    -- Openings
    games_openings.uci_hierarchy_level_1_name,
    games_openings.uci_hierarchy_level_2_name,
    games_openings.uci_hierarchy_level_7_name,
    games_openings.opener_7_moves,
    -- Stats
    games_stats.nb_moves,
    games_stats.prct_time_remaining_playing_early,
    games_stats.prct_time_remaining_playing_mid,
    games_stats.prct_time_remaining_playing_late,
    games_stats.nb_massive_blunder_playing,
    games_stats.has_throw_blunder_playing,
    games_stats.has_throw_massive_blunder_playing,
    games_stats.has_throw_massive_blunder_playing_early,
    games_stats.has_throw_massive_blunder_playing_mid,
    games_stats.has_throw_massive_blunder_playing_late,
    games_stats.has_throw_blunder_playing_early,
    games_stats.has_throw_blunder_playing_mid,
    games_stats.has_throw_blunder_playing_late,
    games_stats.has_missed_opportunity_blunder_playing,
    games_stats.has_missed_opportunity_massive_blunder_playing,
    games_stats.has_missed_opportunity_massive_blunder_playing_early,
    games_stats.has_missed_opportunity_massive_blunder_playing_mid,
    games_stats.has_missed_opportunity_massive_blunder_playing_late,
    games_stats.has_missed_opportunity_blunder_playing_early,
    games_stats.has_missed_opportunity_blunder_playing_mid,
    games_stats.has_missed_opportunity_blunder_playing_late,
    games_stats.first_blunder_massive_blunder_playing_prct_time_remaining,
    games_stats.first_massive_blunder_playing_prct_time_remaining,
    games_stats.first_missed_opp_massive_blunder_playing_prct_time_remaining,
    games_stats.first_throw_massive_blunder_playing_prct_time_remaining
FROM {{ ref('fct_games_stats') }} games_stats
LEFT OUTER JOIN {{ ref('dim_games_openings') }} games_openings
    USING (username, uuid)
LEFT OUTER JOIN {{ ref('dim_games') }} games_info
    USING (username, uuid)
WHERE TRUE
    AND playing_rating_range = opponent_rating_range
    AND playing_result IN ('Win', 'Lose')
    -- AND username = 'Zundorn'
    -- AND time_control = '300+5'
    -- AND playing_rating_range = '0800-1000'
ORDER BY end_time DESC