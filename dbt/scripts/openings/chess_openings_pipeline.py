import sys
import os
import pandas as pd
from datetime import datetime
from sqlalchemy import text
import yaml

sys.path.append(os.path.abspath('..'))
from helper import get_engine 

print("Starting chess openings data loading")

# Load configuration from config.yml
config_path = os.path.join(os.path.abspath('..'), 'config.yml')
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

target_schema   = config["postgres"]["schemas"]["openings"]
target_table    = config["postgres"]["tables"]["openings"]

# Data Read
try:
    # Read the Parquet file directly from the Hugging Face dataset URL
    print("Reading data from Parquet file on Hugging Face...")
    df = pd.read_parquet("hf://datasets/Lichess/chess-openings/data/train-00000-of-00001.parquet")
    print(f"Data fetched successfully — {len(df)} rows loaded.")
except Exception as e:
    print(f"Error reading Parquet file: {e}")
    sys.exit(1)

# Data Load
if not df.empty:

    df["log_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df = df.drop(columns=['img'], errors='ignore') # Drop 'img' column which contains incompatible data type
    engine = get_engine()

    try:
        # Create the schema if it doesn't exist
        with engine.begin() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {target_schema}"))
            print(f"Schema '{target_schema}' ensured to exist.")

        df.to_sql(
            name        = target_table,
            con         = engine,
            schema      = target_schema,    
            if_exists   = 'replace', # Overwrite the table if it exists
            index       = False # Ignore the df index
        )

        print(f"Inserted {len(df)} rows into `{target_schema}.{target_table}`.")

    except Exception as e:
        print(f"Database operation failed: {e}")
        sys.exit(1)

else:
    print("No rows were loaded from the Parquet file.")

print("Finished chess openings data loading")