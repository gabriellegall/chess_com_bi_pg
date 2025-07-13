import subprocess
import sys
import time
import requests
from dotenv import load_dotenv
import os

def run_pipeline_forever():

    load_dotenv()
    subprocess.run(["dbt", "test"], check=True)

if __name__ == "__main__":
    run_pipeline_forever()