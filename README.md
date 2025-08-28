# ♟️ Overview

## Purpose
This project is an end-to-end data solution aiming to extract information from chess.com and construct insightful analysis on the player's performance.
The key questions answered are:
- "Do I manage to beat stronger players and improve ?"
- "Am I weaker at specific game phases on average ?"
- "Do I manage to reduce the frequency at which I make blunders in my games ?"
- "Do I make more or less blunders compared to other similar players ? Is it true for all game phases ?"
- "What are the games I should review to address the most important issues I have ?"
- "Do I make big mistakes when I am under time pressure ?"

Here are some previews of the Metabase dashboard:
![Illustration 1](https://github.com/gabriellegall/chess_com_bi/blob/main/images/metabase_page_1.png)
![Illustration 3](https://github.com/gabriellegall/chess_com_bi/blob/main/images/metabase_page_3.png)

Here are some previews of the Streamlit dashboard:


## Repository
This repository contains all the scripts aiming to: 
1. Set-up a Postgres database
2. Extract the games played data from the chess.com API and load it in Postgres.
3. Extract the individual moves for each game played, evaluate the position using the Stockfish engine, and load it in Postgres.
4. Construct a data model using DBT to define metrics and dimensions (blunders, game phases, ELO ranges, etc.).
5. Deploy dashboards via Streamlit and Metabase

# 🛠️ Technical overview
## Tools
- Data extraction (API): **Python** (with [DLT - Data Load Tool library](https://dlthub.com/docs/dlt-ecosystem/verified-sources/chess))
- Data pre-processing (regex parsing): **Python**
- Chess evaluation: **Stockfish engine** (with Python)
- Data storage & compute: **Postgres**
- Data transformation: **DBT** (on Docker)
- Data visualization: **Metabase & Streamlit** (on Docker)
- Documentation: **DBT Docs**
- Deployment: **from Docker Hub**, with **Docker Compose** including [**Towerwatch**](https://github.com/containrrr/watchtower)
- Pipeline monitoring: [**Healthcheck.io**](https://healthchecks.io/)

## Requirements
- Python
- Docker
- Makefile

## Commands
This project is fully dockerized can be executed locally or deployed on a server.

### Local execution
1. Rename the `.env.example` file to `.env` and update the DB_NAME, DB_USER, DB_PASSWORD with the values of your choice.
2. Using Docker Desktop, run `docker-compose up -d`

You can also choose to install the `requirements.txt` in virtual environment and run the commands to the dockerized Postgres DB:
- `make run_all`: run the continous pipeline with DBT 
- `make run_all_with_reset`: DROP all schemas (except Stockfish processed games) + run the continous pipeline with DBT (full refresh)
- `make run_dbt_full_refresh`: run DBT full-refresh once
- `make run_dbt_test`: run DBT tests
- `make run_dbt_compile`: run DBT compile
- `make run_dbt_doc`: run DBT docs generate & docs serve
- `make test_dbt_doc`: run a Python test to ensure that the documentation is consistent between the DBT YAML files and the `doc.md`file centralizing definitions

### Server deployment (VPS)
1. Rename the `.env.example` file to `.env` and update the DB_NAME, DB_USER, DB_PASSWORD with the values of your choice.
2. copy the `.env` file to a project repository on your server.
3. copy the `docker-compose.yml` to the same project repository on your server.
4. run the command `docker-compose up -d`

# 📂 Project

## Data extraction
The script `chess_games_pipeline.py` gets the data from the chess.com API using the DLT library with the `chess` package and loads it in Postgres.
It uses the `config.yml` to define usernames and history depth to be queried, as well as Postgres project information with table names to be used.

### Incremental strategy
The chess.com games information are partitioned by username and month on the API requests. 
Therefore, the `__init__.py` script in the `chess`package has been modified to query only the partitions that are greater than or equal to the latest partitions integrated in Postgres for each username. Before this custom development, the `chess` package only supported full loads or simply did not update the partitions for the current month. 

## Stockfish evaluation
The script `chess_games_moves_pipeline.py` reads the integrated chess.com data and parses the `[pgn]` field to extract the individual game moves and evaluate a score using the Stockfish engine.
It uses the `config.yml` to define the Postgres project information with table names to be used.

### Incremental strategy 
Only games not yet processed are processed by the Stockfish engine. To identify those games, a query is executed in Postgres, comparing the games loaded with the games loaded for which game moves have been already evaluated. This query is templated under the `helper.py` file.

## Python pre-processing
The script `chess_games_times_pipeline.py` reads the integrated chess.com data and parses the `[pgn]` field to extract the individual game clock times using regex.
It uses the `config.yml` to define the Postgres project information with table names to be used. 

### Incremental strategy 
Only games not yet processed are processed. `chess_games_times_pipeline.py` uses the same SQL query `helper.py` to identify games to be processed incrementally.

# ⏳ Project history
This project is a refactoring of an original GitHub project called [chess_com_bi](https://github.com/gabriellegall/chess_com_bi) developed on BigQuery and orchestrated using GitHub Runners. 

Here are the main changes:
- **Improved the frequency at which the database can be queried**:
    - **Problem:** Frequent queries on BigQuery lead to higher costs, as billing is based on bytes scanned. This required to pre-aggregate most of the final tables before displaying them on Metabase in real-time (as of August 2025, Metabase does not support persistent models for BigQuery).
    - **Solution:** Migrating to a Postgres database hosted on a VPS eliminates query costs and reduces latency by centralizing application components on a single server, thereby improving query performance.
- **Improved data freshness**:
    - **Problem:** Users expect live data in their dashboard (playing a game and then directly checking the results). BigQuery and GitHub Actions are fit for daily batch processing; however, for near real-time data integration (every 10-15 minutes), the free tiers quickly become a bottleneck.
    - **Solution:** Using Postgres and a continously running integration script, we can essentially construct a near real-time BI solution. API calls, Stockfish processing and DBT jobs now execute incrementally every 10 min.
- **Extended analytics**:
    - **Problem:** Metabase is efficient for quick visualization, but unfit for advanced analytics. For instance, it does not support basic box plots, which are essential to benchmark players' performance.
    - **Solution:** A Streamlit application was developped to complement Metabase and produce insightful benchmarks. To avoid having 2 separate data visualization tools, we could imagine to migrate the most insightful Metabase graphs to Streamlit.
- **Simplified data ingestion with DLT**:
    - **Problem:** In the original project, [the code](https://github.com/gabriellegall/chess_com_bi/blob/main/scripts/bq_load_player_games.py) to ingest data from chess.com was custom and did not leverage existing tools like the Python library Data Load Tool (DLT) which has native connectors to chess.com.
    - **Solution:** Leveraging DLT significantly simplified the data ingestion pipeline from chess.com, enhancing code maintenance and readability. While some customization was necessary to implement incremental integration within DLT’s `chess` package, the overall architecture is considerably simpler.
- **Use of Python for data pre-processing**:
    - **Problem:** Unlike BigQuery, Postgres lacks simple native support for complex analytical transformations, such as regex-based array generation.
    - **Solution:** Due to Postgres’ complexity and performance limits, Python was employed for preprocessing tasks such as extracting timestamps from text. [This used to be a BigQuery SQL DBT model in the original project](https://github.com/gabriellegall/chess_com_bi/blob/main/models/intermediate/games_times.sql).






-- Enrich further the Streamlit app
    -- More metrics
    -- Make the graph "Recent games position advantage" with last 7D, 14D, 30D lines
    -- Express time in CET
    -- Openers
