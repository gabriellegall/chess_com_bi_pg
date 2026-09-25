from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv
import pandas as pd
import os

def get_engine() -> Engine:
    """  
    Pass the credentials to connect to the Cube SQL API (Postgres wire protocol).
    """
    load_dotenv()

    cube_user     = os.getenv("CUBE_SQL_USER")
    cube_password = os.getenv("CUBE_SQL_PASSWORD")
    cube_host     = os.getenv("CUBE_SQL_HOST")
    cube_port     = os.getenv("CUBE_SQL_PORT")

    # The database name is not used by Cube
    return create_engine(f"postgresql://{cube_user}:{cube_password}@{cube_host}:{cube_port}/db")

def load_query(sql_path: str, params: dict = None) -> pd.DataFrame:
    """
    Return a df for any .sql path.
    """
    with open(sql_path, "r") as f:
        query = text(f.read())

    engine = get_engine()

    with engine.connect() as connection:
        df = pd.read_sql(query, connection, params=params)
    
    return df