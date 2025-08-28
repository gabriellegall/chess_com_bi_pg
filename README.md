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
1. Extract the games played data from the chess.com API and load it in Postgres.
2. Extract the individual moves for each game played, evaluate the position using the Stockfish engine, and load it in Postgres.
3. Construct a data model using DBT to define metrics and dimensions (blunders, game phases, ELO ranges, etc.).
4. Deploy dashboards via Streamlit and Metabase

# 🛠️ Technical overview
## Tools
- Extract & load API data: **Python** (with [DLT - Data Load Tool library](https://dlthub.com/docs/dlt-ecosystem/verified-sources/chess))
- Data pre-processing (regex parsing): **Python**
- Chess evaluation: **Stockfish engine** (with Python)
- Data storage & compute: **Postgres**
- Data transformation: **DBT** (on Docker)
- Pipeline monitoring: [**Healthcheck.io**](https://healthchecks.io/)
- Data visualization: **Metabase & Streamlit** (on Docker)
- Documentation: **DBT Docs**
- Deployment: **from Docker Hub**, with **Docker Compose** including **Towerwatch**

## Project refactoring
This project is a refactoring of an original GitHub project called [`chess_com_bi`](https://github.com/gabriellegall/chess_com_bi) developed on BigQuery and orchestrated using GitHub Runners. 

Here are the main changes:
- **Improved the frequency at which the database can be queried**. **⚠️ Problem:** querying BigQuery frequently inevitably leads to increased costs since BigQuery charges on the bytes scanned. This required to pre-aggregate most of the final tables before displaying them on Metabase in real-time (as of August 2025, Metabase does not support persistent models for BigQuery). **✅ Solution:** Using a Postgres DB on a VPS aleviates all costs and often results in faster queries because latency is lower when all applications are connected under the same server.
- **Improved data freshness**. **⚠️ Problem:** users expect live data in their dashboard (playing a game and then directly checking the results). Using BigQuery and GitHub as an orchestrator works perfectly for daily batches, but for continous data integration (every 10-15min), the free tier limits are quickly reached. **✅ Solution:** Using Postgres and a continously running integration script, we can essentially construct a near real-time BI solution. API calls, Stockfish processing and DBT jobs execute incrementally every 10 min.
- **Extended analytics**. **⚠️ Problem:** Metabase is efficient for quick visualization, but unfit for advanced analytics. For instance, it does not support basic box plots, which are essential to benchmark players' performance. **✅ Solution:** A Streamlit application was developped to complement Metabase and produce insightful benchmarks. To avoid having 2 separate data visualization tools, we could imagine to migrate the most insightful Metabase graphs to Streamlit.
- **Simplified data ingestion with DLT**. **⚠️ Problem:** In the original project, [the code](https://github.com/gabriellegall/chess_com_bi/blob/main/scripts/bq_load_player_games.py) to ingest data from chess.com was custom and did not leverage existing tools like the Python library Data Load Tool (DLT) which has native connectors to chess.com. Using DLT, I could significantly simplify the code to ingest data from chess.com, making it more robust and easier to understand. It came at the expense of some customization to develop the incremental integration logic in the `chess` package of DLT, but overall the solution is much simpler.
- **Use of Python for data pre-processing**. **⚠️ Problem:** Unfortunately, Postgres is much less equiped for advanced analytical data processing (like generating arrays using regex rules). **✅ Solution:** I had to switch from [SQL](https://github.com/gabriellegall/chess_com_bi/blob/main/models/intermediate/games_times.sql) to Python for some early pre-processing tasks like the extraction of timestamps from text strings. 









-- Enrich further the Streamlit app
    -- More metrics
    -- Make the graph "Recent games position advantage" with last 7D, 14D, 30D lines
    -- Express time in CET
    -- Openers
