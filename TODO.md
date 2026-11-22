- Implement the new dashboard
  - Fix the rating to define it BEFORE the game
- Review project structure and file locations
- Ensure code is clean (commas, etc.)
- Ensure comments are consistent (in-code comments vs in-YAML comments)

1. Stockfish analyses games that dbt then throws away
This is your hard limit, because it's CPU work and no SQL change will speed it up.
helper.py:123 only filters on processable_games_condition. It doesn't apply games_scope_condition, which is the rated / blitz-rapid-bullet / last-12-months filter.
The numbers: 21,549 games have been analysed, but only 6,449 are in dbt's scope. About 70% of the engine time is wasted.
config.yml:17 sets start_month: "2010/01". Each new player brings years of games, at roughly 65 positions per game at depth 12.
The times pipeline has the same leak: 764k rows stored, 441k used.
run_all runs its steps one after another, so a Stockfish backlog also holds back dbt freshness for every player.
Fix: put the scope condition in a shared var, as you did for processable_games_condition, and use it in games_to_process.
1. The daily --full-refresh cancels out your incremental design
At run_all.py:70, once a day the whole history is rebuilt. That includes 1.4M move rows copied into three tables, plus all the window functions in int_game_moves_enriched.
int_game_moves_base and int_game_move_times_base are unfiltered copies of raw. They grow forever, even though the scope is capped at 12 months.
Fix:
Scope or filter those base models, or make them views.
Full-refresh only the models keyed on end_time, since they're the only ones affected by late-arriving games. Or use a lookback window with a delete+insert strategy.
1. Bug: each full refresh deletes the indexes your post-hooks create (confirmed)
What happens:
dbt renames the old table to fct_game_moves__dbt_backup, and the index keeps its name.
The post-hook's CREATE INDEX IF NOT EXISTS idx_fct_game_moves_run_timestamp finds that name already taken, because index names are unique per schema, so it does nothing.
dbt drops the backup table, and the index goes with it.
So the indexes alternate between present and missing from one day to the next. Right now these 6 models have none: int_game_moves_enriched (including its uuid index, which the NOT EXISTS anti-join depends on), int_games_stats, int_games_openings, fct_game_moves, fct_games_stats and fct_games_openings.
Fix: use the native dbt-postgres config indexes=[{'columns': ['run_timestamp']}]. dbt then generates unique names and builds the index on the tmp relation.
1. games_to_process scans a table that keeps growing
helper.py:118 runs SELECT DISTINCT uuid over the whole moves table, which has no uuid index. It runs twice per loop (times and Stockfish), on top of a strpos(pgn, …) over every raw PGN.
It takes 146 ms now, and the cost grows with total moves (about 65× the number of games).
Games that produce 0 moves never get marked as done. They're picked again on every run and use up slots in the LIMIT.
Fix: add a small processed_games(uuid PK, processed_at) table, filled in the same transaction as the moves.
1. The serving layer loads every row, every 10 minutes
Streamlit loads every game row through Cube into pandas, cached for 600 s (data_processing.py:9). To allow that, CUBEJS_DB_QUERY_LIMIT was raised to 1M (docker-compose.yml:64).
Cube has no pre-aggregations and runs in dev mode.
None of the fact tables has an index on the games_sk / players_sk join keys, so the move-level view's joins have to read all of fct_game_moves.
Fix:
Push the aggregations into Cube, which your new dashboard is already moving towards.
Add pre-aggregations with a refresh_key on max(run_timestamp).
Index the join keys.
1. The same data is stored four times
Move-level data exists in 4 copies: raw, int_base, enriched and fct, about 550 MB of the total.
pgn is copied 4 times as well.
A full refresh needs twice the space while it runs.
fct_game_moves stores 3 md5 surrogate keys on every row.
1. Ingestion won't scale to many players
Every loop re-fetches each player's current month, which means N HTTP calls every 10 minutes. With 1,000 players, the parallel dlt.defer calls are likely to hit chess.com 429 errors.
checked_archives is a list that is never pruned. The check url in checked_archives (init.py:145) gets slower as it grows, on the order of n² with thousands of archives.
to_sql uses the default executemany. A times batch of 10k games is about 650k rows inserted one at a time. Use method='multi' or COPY.
I haven't changed anything. Items 1 and 3 give the most for the least work. If you want, I can start with those.