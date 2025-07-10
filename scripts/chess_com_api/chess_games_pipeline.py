import dlt
from chess import source
from dotenv import load_dotenv
import os
import yaml

load_dotenv()

config_path = os.path.join(os.path.abspath('..'), 'config.yml')
with open(config_path, "r") as f:
        config = yaml.safe_load(f)

def run_pipeline():

    credentials = {
        "database":        os.getenv("DB_NAME"),
        "username":        os.getenv("DB_USER"),
        "password":        os.getenv("DB_PASSWORD"),
        "host":            os.getenv("DB_HOST"),
        "port":            int(os.getenv("DB_PORT")),
        "connect_timeout": 15
    }

    pipeline = dlt.pipeline(
        pipeline_name="chess_games_pipeline",
        destination=dlt.destinations.postgres(credentials=credentials),
        dataset_name=config["postgres"]["schemas"]["chess_com_api"],
    )

    data = source(
        config["api"]["usernames"],
        start_month=config["api"]["start_month"],
    )

    info = pipeline.run(
        data.with_resources("players_games"),
        write_disposition="merge",
        primary_key=["uuid", "username"]
    )

    print(info)

if __name__ == "__main__":
    run_pipeline()