import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import yaml
from pathlib import Path
from config import get_plot_config, get_section_config
from data_processing    import get_raw_data, get_summary_kpis, calculate_win_loss_draw, min_benchmark_games
from plot_header        import render_summary_header
from page_sections      import render_benchmark_section, render_opening_analysis_section
from ui_filters         import render_sidebar_filters, render_page_filters, apply_filters

st.set_page_config(layout="wide")


@st.cache_data
def _load_dbt_project_config():
    """Loads the dbt_project.yml file."""
    project_root = Path.cwd().parent # The CWD is the 'streamlit' folder, so we go up one level to the project root.
    config_path = project_root / "dbt" / "dbt_project.yml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

### --- Main Application ---

# Load initial data
raw_data                    = get_raw_data()
dbt_config                  = _load_dbt_project_config()
dbt_game_phases_config      = dbt_config.get("vars", {}).get("game_phases", {})
dbt_score_thresholds_config = dbt_config.get("vars", {}).get("score_thresholds", {})
plot_config                 = get_plot_config(dbt_game_phases_config, dbt_score_thresholds_config)
section_config              = get_section_config(dbt_game_phases_config, dbt_score_thresholds_config)

st.title("Chess.com Player Performance Benchmark")

### --- Sidebar selection ---
all_usernames = sorted(raw_data["username_global"].unique())
default_user = "Zundorn" if "Zundorn" in all_usernames else all_usernames[0]
selected_username_default = st.session_state.get("selected_username", default_user)
if selected_username_default not in all_usernames:
    selected_username_default = default_user

selected_username = st.sidebar.selectbox(
    "Select a Player to Analyze",
    options=all_usernames,
    index=all_usernames.index(selected_username_default),
    key="selected_username"
)

last_n_games = st.sidebar.slider(
    "Number of recent games to analyze",
    min_value=10,
    max_value=60,
    value=30,
    step=1,
    key="last_n_games"
)

### --- Dependent filters ---
user_specific_data = raw_data[raw_data["username_global"] == selected_username]

# Define filter fields for each section 
fields_sidebar_filter   = ["time_control", "playing_rating_range"]
fields_benchmark_filter = ["playing_as", "playing_result"]
fields_opener_filter    = ["playing_as"]

# Render and get sidebar filters
sidebar_selections = render_sidebar_filters(user_specific_data, fields_sidebar_filter)

### --- Summary KPIs header --- 

# Apply filters
df_sidebar_filtered = user_specific_data.copy()
df_sidebar_filtered = apply_filters(df_sidebar_filtered, sidebar_selections)

if df_sidebar_filtered.empty:
    st.warning("No data available for the selected filters.")

# Render the summary KPIs
else:
    with st.container(border=True):
        st.header(f"How is {selected_username} performing?")
        df_sidebar_filtered = calculate_win_loss_draw(df_sidebar_filtered)
        summary_kpis = get_summary_kpis(df_sidebar_filtered, selected_username, last_n_games)
        render_summary_header(summary_kpis, last_n_games)

### --- Benchmark --- 
benchmark_selections = render_page_filters(user_specific_data, fields_benchmark_filter, context="benchmark", add_all=True)
render_benchmark_section(
    raw_data=raw_data,
    selected_username=selected_username,
    last_n_games=last_n_games,
    sidebar_selections=sidebar_selections,
    benchmark_selections=benchmark_selections,
    section_config=section_config,
    plot_config=plot_config,
    min_benchmark_games=min_benchmark_games,
)

### --- Opening Move Analysis ---
opener_selections = render_page_filters(user_specific_data, fields_opener_filter, context="opener")
list_dim = ["uci_hierarchy_level_1_name", "uci_hierarchy_level_2_name", "uci_hierarchy_level_7_name", "opener_7_moves"]
render_opening_analysis_section(
    user_specific_data=user_specific_data,
    selected_username=selected_username,
    last_n_games=last_n_games,
    sidebar_selections=sidebar_selections,
    opener_selections=opener_selections,
    list_dim=list_dim,
)

