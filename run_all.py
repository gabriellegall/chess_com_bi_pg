import subprocess
import sys
import time
import requests
from dotenv import load_dotenv
import os

def run_pipeline_forever():
    load_dotenv()

    URL = os.getenv("HEALTHCHECK_URL")
    URL_DBT_TEST = os.getenv("HEALTHCHECK_URL_DBT_TEST") 
    execution_count = 0

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
            subprocess.run(["dbt", "seed"], check=True)
            subprocess.run(["dbt", "run"], check=True)

            # Healthcheck
            requests.get(URL, timeout=5)
            print(f"✅ Healthcheck ping sent.")
            
            # DBT test
            execution_count += 1
            if execution_count % 100 == 0:
                print(f"Running dbt test (execution {execution_count})")
                test_result = subprocess.run(["dbt", "test"], capture_output=True, text=True)
                
                # Healthcheck
                if test_result.returncode == 0:
                    print("✅ dbt test passed. Pinging success URL.")
                    requests.get(URL_DBT_TEST, timeout=5)
                else:
                    print("❌ dbt test failed. Pinging failure URL.")
                    print(test_result.stderr)
                    requests.get(URL_DBT_TEST + "/fail", timeout=5)

            # Sleep
            time.sleep(60)

        except Exception as e:
            requests.get(URL + "/fail", timeout=5)
            print("❌ Healthcheck failure ping sent.")
            print(e)
            sys.exit(1)

if __name__ == "__main__":
    run_pipeline_forever()