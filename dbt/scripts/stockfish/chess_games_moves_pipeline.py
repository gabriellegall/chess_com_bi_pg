import sys
import os
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.types import DateTime
import chess.pgn
import chess.engine
import io
import platform
import shutil
import glob
import time
import multiprocessing
from pathlib import Path

sys.path.append(os.path.abspath('..'))
from helper import get_engine, games_to_process, load_config, get_table_settings, create_index_if_not_exists


def _extract_stockfish_version(path_str: str) -> tuple:
    path = Path(path_str)
    # Expected folder shape: .../stockfish_<version>/stockfish*.exe
    parent_name = path.parent.name
    if parent_name.startswith("stockfish_"):
        raw = parent_name.replace("stockfish_", "")
        parts = []
        for p in raw.split("."):
            if p.isdigit():
                parts.append(int(p))
            else:
                parts.append(0)
        return tuple(parts)
    return tuple()

def _analyze_chess_game(uuid: str, pgn: str, engine: chess.engine.SimpleEngine, depth: int) -> pd.DataFrame:
    # Load the PGN
    game = chess.pgn.read_game(io.StringIO(pgn))

    if game is None:
        print(f"Warning: Failed to parse PGN for game {uuid}")
        return pd.DataFrame(columns=["uuid", "move_number", "move", "score_white"])

    # Initialize lists to hold data
    move_numbers = []
    moves = []
    scores_white = []

    # Analyze the game (game=uuid resets the engine hash between games, keeps it within a game)
    board = game.board()
    limit = chess.engine.Limit(depth=depth)

    for i, move in enumerate(game.mainline_moves(), 1):
        board.push(move)
        info = engine.analyse(board, limit, game=uuid)
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


# One Stockfish process per worker, started once and reused for all the games of that worker
_worker_engine = None
_worker_depth = None


def _init_worker(engine_path: str, depth: int) -> None:
    global _worker_engine, _worker_depth
    _worker_engine = chess.engine.SimpleEngine.popen_uci(engine_path)
    _worker_depth = depth


def _analyze_game_worker(uuid_pgn: tuple) -> pd.DataFrame:
    uuid, pgn = uuid_pgn
    return _analyze_chess_game(uuid, pgn, _worker_engine, _worker_depth)


def _analyze_multiple_games(games: pd.DataFrame, engine_path: str, depth: int, workers: int) -> pd.DataFrame:
    tasks = list(games[["uuid", "pgn"]].itertuples(index=False, name=None))
    game_dfs = []
    start = time.perf_counter()

    def _log_progress():
        n = len(game_dfs)
        if n % 10 == 0 or n == len(tasks):
            print(f"Processed {n}/{len(tasks)} games ({time.perf_counter() - start:.0f}s)", flush=True)

    if workers <= 1:
        _init_worker(engine_path, depth)
        try:
            for task in tasks:
                game_dfs.append(_analyze_game_worker(task))
                _log_progress()
        finally:
            _worker_engine.quit()
    else:
        # multiprocessing.Pool (not ProcessPoolExecutor): its exit terminates the workers. python-chess keeps a
        # non-daemon thread alive per engine, so workers would never exit by themselves and the pool would hang.
        with multiprocessing.Pool(processes=workers, initializer=_init_worker, initargs=(engine_path, depth)) as pool:
            for game_df in pool.imap(_analyze_game_worker, tasks):
                game_dfs.append(game_df)
                _log_progress()

    # Concatenate all dataframes into one
    return pd.concat(game_dfs, ignore_index=True)

def _get_stockfish_path():
    """Resolve a usable Stockfish executable path across env, PATH and OS defaults.

    Resolution order:
    1) [`STOCKFISH_PATH`] environment variable
    2) `stockfish` available in system PATH
    3) Common install locations (including Chocolatey versioned folders on Windows)
    """
    candidates = []

    env_path = os.getenv("STOCKFISH_PATH")
    if env_path:
        candidates.append(env_path)

    stockfish_in_path = shutil.which("stockfish")
    if stockfish_in_path:
        candidates.append(stockfish_in_path)

    if platform.system() == "Windows":
        program_files = os.environ.get("ProgramFiles", "C:/Program Files")
        choco_globs = [
            os.path.join(program_files, "ChessEngines", "stockfish_*", "stockfish-windows-x86-64-avx2.exe"),
            os.path.join(program_files, "ChessEngines", "stockfish_*", "stockfish-windows-x86-64.exe"),
            os.path.join(program_files, "ChessEngines", "stockfish_*", "stockfish*.exe"),
        ]
        discovered = []
        for pattern in choco_globs:
            discovered.extend(glob.glob(pattern))
        candidates.extend(sorted(set(discovered), key=_extract_stockfish_version, reverse=True))

        candidates.extend([
            "C:/Program Files/Stockfish/stockfish.exe",
            "C:/Program Files/stockfish/stockfish.exe",
        ])
    else:
        candidates.extend([
            "/usr/games/stockfish",
            "/usr/bin/stockfish",
        ])

    for candidate in candidates:
        resolved = os.path.expandvars(os.path.expanduser(candidate))
        if os.path.isfile(resolved):
            return resolved

    raise FileNotFoundError(
        "Stockfish executable not found. Set STOCKFISH_PATH to your stockfish binary "
        "or install stockfish so it is available in PATH."
    )

def main() -> int:
    """Analyse one batch of unprocessed games and return the number of games processed (0 = backlog empty)."""
    print("Starting games moves processing")

    # Import the data to process
    config = load_config()

    target_schema   = config["postgres"]["schemas"]["stockfish"]
    target_table, target_index_field = get_table_settings(config, "stockfish")

    engine  = get_engine()
    stockfish_config = config["postgres"]["tables"]["stockfish"]
    games_limit = stockfish_config["games_limit"]
    depth       = stockfish_config.get("depth", 12)
    workers     = stockfish_config.get("workers", 1)
    query   = games_to_process(engine, schema=target_schema, table=target_table, limit=games_limit)
    games   = pd.read_sql(query, engine)
    print(f"Query executed successfully — {len(games)} rows fetched.")

    if not games.empty:
        games = games[['uuid', 'pgn']]

        # Calculate all games moves for all games
        engine_path = _get_stockfish_path()
        print(f"Analysing with Stockfish depth={depth}, workers={workers}")
        games_moves = _analyze_multiple_games(games, engine_path, depth, workers)
        games_moves["log_timestamp"] = datetime.now(tz=timezone.utc)

        with engine.begin() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {target_schema}"))

        games_moves.to_sql(
            name        = target_table,
            con         = engine,
            schema      = target_schema,     
            if_exists   = 'append', # If the table exists
            index       = False, # Ignore the df index   
            dtype       = {'log_timestamp': DateTime(timezone=True)}
        )

        create_index_if_not_exists(engine, target_schema, target_table, target_index_field)

        print(f"Inserted {len(games_moves)} rows into `{target_schema}.{target_table}`.")
    else:
        print("No rows to be inserted.")

    return len(games)


# Guard required: worker processes re-import this module on Windows (spawn)
if __name__ == "__main__":
    main()
