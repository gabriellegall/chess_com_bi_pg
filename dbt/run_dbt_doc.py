import subprocess
import sys
import time
import requests
from dotenv import load_dotenv
import os

def run_pipeline():

    load_dotenv()
    subprocess.run(["dbt", "docs", "generate"], check=True)
    subprocess.run(["dbt", "docs", "serve"], check=True)

if __name__ == "__main__":
    run_pipeline()