import sys
import os
import pandas as pd
import re
from datetime import datetime
from sqlalchemy import text

sys.path.append(os.path.abspath('..'))
from helper import get_engine, games_to_process

def extract_move_data(pgn):
    clocks = re.findall(r'\[%clk (\d+):(\d{2}):(\d{2}(?:\.\d)?)\]', pgn)
    return [
        {
            'move_number': i + 1,
            'time_remaining_seconds': int(h) * 3600 + int(m) * 60 + float(s),
            'time_remaining': f"{h}:{m}:{s}"
        }
        for i, (h, m, s) in enumerate(clocks)
    ]

target_schema   = "stg_times"
target_table    = "player_games_times"

engine  = get_engine()
query   = games_to_process(engine, schema=target_schema, table=target_table)
games   = pd.read_sql(query, engine)
print(f"✅ Query executed successfully — {len(games)} rows fetched.")

if not games.empty:
    games['move_data'] = games['pgn'].apply(extract_move_data)
    
    games_expanded = games.explode('move_data', ignore_index=True)
    games_expanded[['move_number', 'time_remaining_seconds', 'time_remaining']] = pd.json_normalize(games_expanded['move_data'])
    games_expanded["log_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    games_expanded = games_expanded.drop(columns=['move_data', 'pgn'])

    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {target_schema}"))

    games_expanded.to_sql(
        name        = target_table,
        con         = engine,
        schema      = target_schema,
        if_exists   = 'append',
        index       = False
    )

    print(f"✅ Inserted {len(games_expanded)} rows into `{target_schema}.{target_table}`.")
else:
    print("ℹ️ No rows to be inserted.")