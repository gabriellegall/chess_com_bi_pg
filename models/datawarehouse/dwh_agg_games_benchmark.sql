{{ config(
    enabled=True,
    materialized='table'
) }}

WITH username_info AS (
  SELECT 
    username,
    time_class,
    playing_rating_range,
    game_phase_key,
    aggregation_level,
    COUNT(*) FILTER (WHERE nb_blunder_playing > 0) * 1.0 / COUNT(*) AS rate_nb_blunder_playing,
    COUNT(*) FILTER (WHERE nb_massive_blunder_playing > 0) * 1.0 / COUNT(*) AS rate_nb_massive_blunder_playing,
    COUNT(*) FILTER (WHERE first_massive_blunder_playing_prct_time_remaining > 0.5) * 1.0 / COUNT(*) AS rate_nb_massive_blunder_playing_prct_time_50,
    COUNT(*) FILTER (WHERE first_massive_blunder_playing_prct_time_remaining > 0.7) * 1.0 / COUNT(*) AS rate_nb_massive_blunder_playing_prct_time_70,
    COUNT(*) FILTER (WHERE first_massive_blunder_playing_prct_time_remaining > 0.9) * 1.0 / COUNT(*) AS rate_nb_massive_blunder_playing_prct_time_90,
    COUNT(*) FILTER (WHERE nb_throw_playing > 0) * 1.0 / COUNT(*) AS rate_nb_throw_playing,
    COUNT(*) FILTER (WHERE nb_missed_opportunity_playing > 0) * 1.0 / COUNT(*) AS rate_nb_missed_opportunity_playing,
    AVG(median_score_playing) AS avg_score_playing,
    COUNT(*) AS nb_games
  FROM {{ ref ('dwh_agg_games_with_moves') }}
  WHERE playing_rating_range = opponent_rating_range
    AND end_time_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
  GROUP BY username, time_class, playing_rating_range, game_phase_key, aggregation_level
  HAVING COUNT(*) > {{ var('datamart')['min_games_played'] }}
),

benchmark_metrics AS (
  SELECT 
    u.username,
    u.game_phase_key,
    u.time_class,
    u.playing_rating_range,
    u.aggregation_level,
    
    -- Playing metrics
    MIN(u.rate_nb_blunder_playing) AS rate_nb_blunder_playing,
    MIN(u.rate_nb_massive_blunder_playing) AS rate_nb_massive_blunder_playing,
    MIN(u.rate_nb_massive_blunder_playing_prct_time_50) AS rate_nb_massive_blunder_playing_prct_time_50,
    MIN(u.rate_nb_massive_blunder_playing_prct_time_70) AS rate_nb_massive_blunder_playing_prct_time_70,
    MIN(u.rate_nb_massive_blunder_playing_prct_time_90) AS rate_nb_massive_blunder_playing_prct_time_90,
    MIN(u.rate_nb_throw_playing) AS rate_nb_throw_playing,
    MIN(u.rate_nb_missed_opportunity_playing) AS rate_nb_missed_opportunity_playing,
    MIN(u.nb_games) AS nb_games,

    -- Benchmark
    COUNT(*) FILTER (WHERE gp.nb_blunder_playing > 0) * 1.0 / COUNT(*) AS bench_rate_nb_blunder_playing,
    COUNT(*) FILTER (WHERE gp.nb_massive_blunder_playing > 0) * 1.0 / COUNT(*) AS bench_rate_nb_massive_blunder_playing,
    COUNT(*) FILTER (WHERE gp.first_massive_blunder_playing_prct_time_remaining > 0.5) * 1.0 / COUNT(*) AS bench_rate_nb_massive_blunder_playing_prct_time_50,
    COUNT(*) FILTER (WHERE gp.first_massive_blunder_playing_prct_time_remaining > 0.7) * 1.0 / COUNT(*) AS bench_rate_nb_massive_blunder_playing_prct_time_70,
    COUNT(*) FILTER (WHERE gp.first_massive_blunder_playing_prct_time_remaining > 0.9) * 1.0 / COUNT(*) AS bench_rate_nb_massive_blunder_playing_prct_time_90,
    COUNT(*) FILTER (WHERE gp.nb_throw_playing > 0) * 1.0 / COUNT(*) AS bench_rate_nb_throw_playing,
    COUNT(*) FILTER (WHERE gp.nb_missed_opportunity_playing > 0) * 1.0 / COUNT(*) AS bench_rate_nb_missed_opportunity_playing,
    COUNT(*) AS bench_nb_games

  FROM username_info u
  LEFT JOIN {{ ref ('dwh_agg_games_with_moves') }} gp
    ON gp.username <> u.username
    AND gp.game_phase_key = u.game_phase_key
    AND gp.time_class = u.time_class
    AND gp.playing_rating_range = u.playing_rating_range
  WHERE gp.playing_rating_range = gp.opponent_rating_range
  GROUP BY 
    u.username, u.game_phase_key, u.time_class, 
    u.playing_rating_range, u.aggregation_level
  HAVING COUNT(*) > {{ var('datamart')['min_games_played'] }}
),

define_most_frequent_range AS (
  SELECT DISTINCT ON (username, time_class)
    username,
    time_class,
    playing_rating_range AS most_relevant_playing_rating_range,
    nb_games
  FROM benchmark_metrics
  WHERE aggregation_level = 'Games'
  ORDER BY username, time_class, nb_games DESC
)

SELECT 
  benchmark.*
FROM benchmark_metrics benchmark
INNER JOIN define_most_frequent_range frequent
  ON  benchmark.username = frequent.username
  AND benchmark.time_class = frequent.time_class
  AND benchmark.playing_rating_range = frequent.most_relevant_playing_rating_range