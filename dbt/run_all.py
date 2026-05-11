"""Run the chess data pipelines in a continuous loop.

Flow per iteration:
- Run source pipelines (chess.com API optionally, game times, stockfish moves)
- Run dbt seed
- Run dbt build with --full-refresh once per day, otherwise regular dbt build
- Ping healthcheck URLs and run dbt tests every 100 iterations
- Sleep for SLEEP_TIME seconds, then repeat
"""

import subprocess
import sys
import time
import requests
from dotenv import load_dotenv
import os
from datetime import date

def run_pipeline_forever():
    load_dotenv()

    URL = os.getenv("HEALTHCHECK_URL")
    URL_DBT_TEST = os.getenv("HEALTHCHECK_URL_DBT_TEST")
    
    # Configuration options
    SKIP_CHESS_COM_API = os.getenv("SKIP_CHESS_COM_API", "false").lower() == "true" # Default: False
    SLEEP_TIME = int(os.getenv("SLEEP_TIME", "600")) # Default: 600 seconds (10 minutes)
    
    execution_count = 0
    last_full_refresh_date = None

    # openings
    subprocess.run(
        [sys.executable, "chess_openings_pipeline.py"],
        check=True,
        cwd="scripts/openings"
    )

    while True:
        try:
            # chess.com API (conditional)
            if not SKIP_CHESS_COM_API:
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
            today = date.today()
            # Run a full-refresh only once per calendar day. All other loop iterations use a regular incremental build.
            if last_full_refresh_date != today:
                print("Running daily dbt full-refresh build")
                subprocess.run(
                    ["dbt", "build", "--full-refresh", "--exclude", "dbt_project_evaluator"],
                    check=True,
                )
                last_full_refresh_date = today
            else:
                print("Running regular dbt build (daily full-refresh already completed)")
                subprocess.run(["dbt", "build", "--exclude", "dbt_project_evaluator"], check=True)

            # Healthcheck
            requests.get(URL, timeout=5)
            print(f"Healthcheck ping sent.")
            
            # DBT test - every N executions
            execution_count += 1
            if execution_count % 100 == 0:
                print(f"Running dbt test (execution {execution_count})")
                test_result = subprocess.run(["dbt", "test", "--exclude", "dbt_project_evaluator"], capture_output=True, text=True)
                
                # Healthcheck
                if test_result.returncode == 0:
                    print("dbt test passed. Pinging success URL.")
                    requests.get(URL_DBT_TEST, timeout=5)
                else:
                    print("dbt test failed. Pinging failure URL.")
                    print(test_result.stderr)
                    requests.get(URL_DBT_TEST + "/fail", timeout=5)

            # Sleep
            time.sleep(SLEEP_TIME)

        except Exception as e:
            requests.get(URL + "/fail", timeout=5)
            print("Healthcheck failure ping sent.")
            print(e)
            sys.exit(1)

if __name__ == "__main__":
    run_pipeline_forever()