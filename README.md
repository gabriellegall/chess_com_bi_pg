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
- Data pre-processing: **Python**
- Chess evaluation: **Stockfish engine** (with Python)
- Data storage & compute: **Postgres**
- Data transformation: **DBT** (on Docker)
- Pipeline monitoring: [**Healthcheck.io**](https://healthchecks.io/)
- Data visualization: **Metabase & Streamlit** (on Docker)
- Documentation: **DBT Docs**
- Deployment: **Docker Compose**

## Project refactoring
This project is a refactoring of an original project called `chess_com_bi` developed on BigQuery and orchestrated using GitHub. 

Here are the main changes:
- **Improved the frequency at which the database can be queried**. **⚠️ Problem:** querying BigQuery frequently inevitably leads to increased costs since BigQuery charges on the bytes scanned. This required to pre-aggregate most of the final tables before displaying them on Metabase in real-time (as of August 2025, Metabase does not support persistent models for BigQuery). **✅ Solution:** Using a Postgres DB on a VPS aleviates all costs and often results in faster queries because latency is lower when all applications are connected under the same server.

- Switch from BigQuery to Postgres: mostly for financial reasons. Postgres is free while BigQuery charges on the bytes scanned. This required to pre-aggregate most of the final tables before displaying them on Metabase in real-time. Postgres on Docker is also more reactive (lower latency) and users can be indexed for fast querying.
- Switch from refresh every 24H to refresh every 15min: 


-- Enrich further the Streamlit app
    -- More metrics
    -- Make the graph "Recent games position advantage" with last 7D, 14D, 30D lines
    -- Express time in CET
    -- Openers
