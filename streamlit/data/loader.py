from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv
import pandas as pd
import os

def get_engine() -> Engine:
    """  
    Pass the credentials to connect to the Postgres engine DB.
    """
    load_dotenv()

    db_name     = os.getenv("DB_NAME")
    db_user     = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host     = os.getenv("DB_HOST")
    db_port     = os.getenv("DB_PORT")

    return create_engine(f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")

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