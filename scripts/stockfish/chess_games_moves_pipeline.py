import sys
import os
import pandas as pd
from datetime import datetime
from sqlalchemy import text
import chess.pgn
import chess.engine
import io
import asyncio
import platform
import yaml

sys.path.append(os.path.abspath('..'))
from helper import get_engine, games_to_process

print("🚀 Starting games moves processing")

def analyze_chess_game(uuid: str, pgn: str, engine_path: str) -> pd.DataFrame:
    # Load the PGN
    game = chess.pgn.read_game(io.StringIO(pgn))

    if game is None:
        print(f"Warning: Failed to parse PGN for game {uuid}")
        return pd.DataFrame(columns=["uuid", "move_number", "move", "score_white"])

    # Initialize lists to hold data
    move_numbers = []
    moves = []
    scores_white = []

    # Analyze the game
    with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
        board = game.board()

        for i, move in enumerate(game.mainline_moves(), 1):
            board.push(move)
            info = engine.analyse(board, chess.engine.Limit(time=0.1))
            score_white = info["score"].white().score(mate_score=1000)

            # Append data to lists
            move_numbers.append(i)
            moves.append(move.uci())
            scores_white.append(score_white)

    # Create a DataFrame
    df = pd.DataFrame({
        "uuid": [uuid] * len(move_numbers),
        "move_number": move_numbers,
        "move": moves,
        "score_white": scores_white
    })

    return df

def analyze_multiple_games(games: pd.DataFrame, engine_path: str) -> pd.DataFrame:
    game_dfs = []
    processed_games = 0

    # Iterate over each game in the dataframe
    for _, row in games.iterrows():
        uuid = row['uuid']
        pgn = row['pgn']

        # Analyze the game and append the result to the list
        game_df = analyze_chess_game(uuid, pgn, engine_path)
        game_dfs.append(game_df)

        # Increment and print the number of processed games
        processed_games += 1
        print(f"Processed {processed_games} games", flush=True)

    # Concatenate all dataframes into one
    return pd.concat(game_dfs, ignore_index=True)

def get_stockfish_path():
    if platform.system() == "Windows":
        if hasattr(asyncio, 'WindowsProactorEventLoopPolicy'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        return "C:/Program Files/ChessEngines/stockfish_16/stockfish-windows-x86-64-avx2.exe"
    return "/usr/games/stockfish"

# Import the data to process
config_path = os.path.join(os.path.abspath('..'), 'config.yml')
with open(config_path, "r") as f:
        config = yaml.safe_load(f)

target_schema   = config["postgres"]["schemas"]["stockfish"]
target_table    = config["postgres"]["tables"]["stockfish"]

engine  = get_engine()
query   = games_to_process(engine, schema=target_schema, table=target_table)
games   = pd.read_sql(query, engine)
print(f"✅ Query executed successfully — {len(games)} rows fetched.")

if not games.empty:
    games = games[['uuid', 'pgn']]

    # Calculate all games moves for all games
    engine_path = get_stockfish_path()
    games_moves = analyze_multiple_games(games, engine_path)
    games_moves["log_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {target_schema}"))

    games_moves.to_sql(
        name        = target_table,
        con         = engine,
        schema      = target_schema,     
        if_exists   = 'append', # If the table exists
        index       = False # Ignore the df index   
    )

    print(f"✅ Inserted {len(games_moves)} rows into `{target_schema}.{target_table}`.")
else:
    print("ℹ️ No rows to be inserted.")

