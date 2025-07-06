import pandas as pd
from sqlalchemy import create_engine, inspect
import os
from dotenv import load_dotenv

def get_engine():

    load_dotenv()

    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")

    return create_engine(f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")

def table_with_prefix_exists(engine, schema_name, table_prefix):

    inspector = inspect(engine)
    tables = inspector.get_table_names(schema=schema_name)
    
    return any(t.startswith(table_prefix) for t in tables)

def games_to_process(engine, schema, table):

    # Declare the games table
    schema_games = "stg_chess_com"
    table_games  = "players_games"

    if table_with_prefix_exists(engine, schema, table):

        # Identify new record (to process) from the games table
        query = f"""
        SELECT
            game.uuid,
            MAX(game.pgn) AS pgn
        FROM {schema_games}.{table_games} game
        LEFT JOIN (
            SELECT DISTINCT uuid FROM {schema}.{table}
        ) target_table
        ON game.uuid = target_table.uuid
        WHERE 
            target_table.uuid IS NULL
            AND LENGTH(game.pgn) > 0
            AND game.rules = 'chess'
        GROUP BY 1
        """
    else:
        query = f"SELECT uuid, pgn FROM {schema_games}.{table_games}"
    
    return query