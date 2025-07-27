import pandas as pd
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
import os
from dotenv import load_dotenv
import yaml

def get_engine() -> Engine:

    load_dotenv()

    db_name     = os.getenv("DB_NAME")
    db_user     = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host     = os.getenv("DB_HOST")
    db_port     = os.getenv("DB_PORT")

    return create_engine(f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")

def table_with_prefix_exists(engine: Engine, schema_name: str, table_prefix: str) -> bool:

    inspector = inspect(engine)
    tables = inspector.get_table_names(schema=schema_name)
    
    return any(t.startswith(table_prefix) for t in tables)

def games_to_process(engine: Engine, schema: str, table: str, limit: int = 100) -> str:

    config_path = os.path.join(os.path.abspath('..'), 'config.yml')
    with open(config_path, "r") as f:
            config = yaml.safe_load(f)

    schema_games = config["postgres"]["schemas"]["chess_com_api"]
    table_games  = "players_games" # DLT built-in table name

    if table_with_prefix_exists(engine, schema, table):

        # Identify new record (to process) from the games table
        query = f"""
        SELECT
            game.uuid,
            MAX(game.pgn) AS pgn,
            MAX(end_time) AS end_time
        FROM {schema_games}.{table_games} game
        LEFT JOIN (
            SELECT DISTINCT uuid FROM {schema}.{table}
        ) target_table
        ON game.uuid = target_table.uuid
        WHERE 
            target_table.uuid IS NULL
            AND LENGTH(game.pgn) > 0
            AND game.rules = 'chess'
        GROUP BY game.uuid
        ORDER BY end_time DESC -- Process the fresh games first
        LIMIT {limit}
        """
    else:
        query = f"SELECT uuid, MAX(pgn) AS pgn FROM {schema_games}.{table_games} GROUP BY 1 LIMIT {limit}"
    
    return query