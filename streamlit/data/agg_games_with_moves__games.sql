SELECT 
    username, 
    end_time,
    time_class,
    playing_rating,
    opponent_rating,
    nb_massive_blunder_playing
FROM dwh.dwh_agg_games_with_moves__prep
WHERE aggregation_level = 'Games'
    AND DATE(end_time) > CURRENT_DATE - INTERVAL '3 months'