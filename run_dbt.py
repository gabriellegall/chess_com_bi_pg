import subprocess
import sys
import time
import requests
from dotenv import load_dotenv
import os

def run_pipeline():

    load_dotenv()
    subprocess.run(["dbt", "run", "--select", "dwh_agg_games_with_moves__prep+","--full-refresh"], check=True)

if __name__ == "__main__":
    run_pipeline()