import subprocess
import sys
import time
import requests
from dotenv import load_dotenv
import os

def run_pipeline_forever():

    load_dotenv()
    URL = os.getenv("HEALTHCHECK_URL")

    while True:
        try:

            # chess.com API
            subprocess.run(
                [sys.executable, "chess_games_pipeline.py"],
                check=True,
                cwd="scripts/chess_com_api"
            )

            # chess games times
            subprocess.run(
                [sys.executable, "chess_games_times_pipeline.py"],
                check=True,
                cwd="scripts/games_times"
            )

            # chess games moves
            subprocess.run(
                [sys.executable, "chess_games_moves_pipeline.py"],
                check=True,
                cwd="scripts/stockfish"
            )

            # DBT
            subprocess.run(["dbt", "run"], check=True)

            # Admin
            requests.get(URL, timeout=5)
            print(f"✅ Healthcheck ping sent.")
            time.sleep(300)

        except Exception as e:
            requests.get(URL + "/fail", timeout=5)
            print("❌ Healthcheck failure ping sent.")

            print(e)
            sys.exit(1)

if __name__ == "__main__":
    run_pipeline_forever()