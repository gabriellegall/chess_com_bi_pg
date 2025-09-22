import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import yaml
from pathlib import Path
from config import get_plot_config, get_section_config
from data_processing    import get_raw_data, get_players_aggregates, get_summary_kpis, calculate_win_loss_draw
from plot_benchmark     import render_legend, prepare_section_plot_data, render_plot_section
from plot_header        import render_summary_header
from plot_openers       import render_opening_sunburst

st.set_page_config(layout="wide")

@st.cache_data
def load_dbt_project_config():
    """Loads the dbt_project.yml file."""
    project_root = Path.cwd().parent # The CWD is the 'streamlit' folder, so we go up one level to the project root.
    config_path = project_root / "dbt" / "dbt_project.yml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def render_sidebar_filters(dependent_data: pd.DataFrame, filter_fields: list) -> dict:
    """
    Creates select boxes in the sidebar for each field in `filter_fields`.
    Only shows the values relevant based on the `dependent_data`.
    Returns the user's selections as a dictionary.
    """
    st.sidebar.header("Game Filters")
    selections = {}
    for field in filter_fields:
        options = sorted(list(dependent_data[field].unique()))
        if not options:
            st.sidebar.warning(f"No '{field.replace('_', ' ')}' options.")
            continue

        selected_option = st.sidebar.selectbox(
            f"Select {field.replace('_', ' ').title()}",
            options=options,
            key=f"sidebar_{field}" # ensure Streamlit updates the widget when options change
        )
        selections[field] = selected_option
    return selections

def render_page_filters(
    dependent_data: pd.DataFrame,
    filter_fields: list,
    context: str,
    *,
    style: str = "radio",   # 🔑 "radio" (default) or "dropdown"
    horizontal: bool = True # Only applies if style="radio"
) -> dict:
    """
    Creates select boxes in the main content area for each field in `filter_fields`, arranging them in columns.
    Only shows the values relevant based on the `dependent_data`.
    Returns the user's selections as a dictionary.

    style = "radio"   → horizontal radio buttons
    style = "dropdown"→ searchable drop-down (selectbox)
    """
    selections = {}
    cols = st.columns(len(filter_fields))

    for col, field in zip(cols, filter_fields):
        with col:
            options = sorted(list(dependent_data[field].dropna().unique()))
            if not options:
                st.warning(f"No '{field.replace('_', ' ')}' options.")
                continue

            label = field.replace("_", " ").title()
            key   = f"{context}_{field}"

            if style == "dropdown":
                selections[field] = st.selectbox(label, options, key=key)
            else:  # default to radio
                selections[field] = st.radio(
                    label,
                    options,
                    horizontal=horizontal,
                    label_visibility="collapsed" if horizontal else "visible",
                    key=key
                )
    return selections

def render_page_filters(
    dependent_data: pd.DataFrame,
    filter_fields: list,
    context: str,
    *,
    style: str = "radio",
    horizontal: bool = True,
    add_all: bool = False   # 🔑 NEW
) -> dict:
    """
    Creates select boxes in the main content area for each field in `filter_fields`, arranging them in columns.
    Only shows the values relevant based on the `dependent_data`.
    Returns the user's selections as a dictionary.

    style   = "radio"   → horizontal radio buttons
    style   = "dropdown"→ searchable drop-down (selectbox)
    add_all = True      → adds an 'All' option that applies no filter
    """
    selections = {}
    cols = st.columns(len(filter_fields))

    for col, field in zip(cols, filter_fields):
        with col:
            raw_options = sorted(list(dependent_data[field].dropna().unique()))
            if not raw_options:
                st.warning(f"No '{field.replace('_', ' ')}' options.")
                continue

            # ✅ Add "All" only if requested
            options = ["All"] + raw_options if add_all else raw_options

            label = field.replace("_", " ").title()
            key   = f"{context}_{field}"

            if style == "dropdown":
                # Default to "All" when present
                index = 0 if add_all else 0
                selections[field] = st.selectbox(label, options, key=key, index=index)
            else:
                selections[field] = st.radio(
                    label,
                    options,
                    horizontal=horizontal,
                    label_visibility="collapsed" if horizontal else "visible",
                    key=key,
                    index=0 if add_all else 0
                )
    return selections

### --- Main Application ---

# Load initial data
raw_data                    = get_raw_data()
dbt_config                  = load_dbt_project_config()
dbt_game_phases_config      = dbt_config.get("vars", {}).get("game_phases", {})
dbt_score_thresholds_config = dbt_config.get("vars", {}).get("score_thresholds", {})
plot_config                 = get_plot_config(dbt_game_phases_config, dbt_score_thresholds_config)
section_config              = get_section_config(dbt_game_phases_config, dbt_score_thresholds_config)

st.title("Chess.com Player Performance Benchmark")

### --- Sidebar selection ---
all_usernames = sorted(raw_data["username"].unique())
default_user = "Zundorn" if "Zundorn" in all_usernames else all_usernames[0]

selected_username = st.sidebar.selectbox(
    "Select a Player to Analyze",
    options=all_usernames,
    index=all_usernames.index(st.session_state.get("selected_username", default_user)),
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
user_specific_data = raw_data[raw_data['username'] == selected_username]

# Define filter fields for each section 
fields_sidebar_filter   = ["time_control", "playing_rating_range"]
fields_benchmark_filter = ["playing_as", "playing_result"]
fields_opener_filter    = ["playing_as"]

# Render and get sidebar filters
sidebar_selections = render_sidebar_filters(user_specific_data, fields_sidebar_filter)

### --- Summary KPIs header --- 
# Apply filters
df_sidebar_filtered = user_specific_data.copy()
for field, value in sidebar_selections.items():
    if value:
        df_sidebar_filtered = df_sidebar_filtered[df_sidebar_filtered[field] == value]

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
with st.container(border=True):
    st.header(f"How does {selected_username} compare to other similar players?")

    # Render and get benchmark filters
    branchmark_selections = render_page_filters(user_specific_data, fields_benchmark_filter, context="benchmark")

    # Combine all selections into a single dictionary
    all_selections = {**sidebar_selections, **branchmark_selections}

    # Apply the combined filters to the entire dataset
    df_filtered_benchmark = raw_data.copy()
    for field, value in all_selections.items():
        if value:
            df_filtered_benchmark = df_filtered_benchmark[df_filtered_benchmark[field] == value]

    # Get the aggregated data for all players
    df_player_agg = get_players_aggregates(df_filtered_benchmark, plot_config)

    # Add explanatory context text based on the filter selection 
    st.markdown(f"""
    In this section, we compare the performance of **{selected_username}** with other similar players (n={len(df_player_agg)}), holding constant: 
    - Color played: **{branchmark_selections.get('playing_as', 'N/A')}**
    - Playing result: **{branchmark_selections.get('playing_result', 'N/A')}**
    - Time control: **{sidebar_selections.get('time_control', 'N/A')}**
    - Rating range: **{sidebar_selections.get('playing_rating_range', 'N/A')}**
    """)

    # Render plots for each section
    if df_player_agg.empty:
        st.warning("No player data available for the selected filters. Please adjust your selections.")
    else:
        username_to_highlight = selected_username
        if username_to_highlight not in df_player_agg['username'].unique():
            st.warning(f"'{username_to_highlight}' has fewer than 30 games for the selected filters and cannot be benchmarked. Please adjust the filters or select another player.")
        else:
            # Render the legend
            render_legend(username=username_to_highlight, last_n_games=last_n_games)

            # Import the data for each section and each plot
            all_section_plot_data = prepare_section_plot_data(
                section_config, plot_config, df_filtered_benchmark, username_to_highlight, last_n_games
            )

            # For each section, render the plots
            for prepared_section_data in all_section_plot_data:
                with st.container(border=True):
                    render_plot_section(prepared_section_data, df_player_agg, last_n_games)

### --- Opening Move Analysis ---
with st.container(border=True):
    st.header(f"How does {selected_username} perform on the various openers?")
    st.markdown("In this section, we explore the win rate on the various openings played:")

    # Standard opener filters (affect sunburst only)
    opener_selections = render_page_filters(user_specific_data, fields_opener_filter, context="opener")

    # Apply standard opener filters for the sunburst
    all_selections = {**sidebar_selections, **opener_selections}

    df_filtered_opener = user_specific_data.copy()
    for field, value in all_selections.items():
        if value:
            df_filtered_opener = df_filtered_opener[df_filtered_opener[field] == value]

    # Sunburst charts
    render_opening_sunburst(df_filtered_opener, last_n_games=last_n_games)

    # ✅ Apply additional filters only to the raw table
    st.subheader("Raw data")

    opener_raw_selections = render_page_filters(
        user_specific_data, ["opener_2_moves", "opener_4_moves", "opener_6_moves"], context="opener_raw", style="dropdown", add_all=True
    )

    all_selections = {**sidebar_selections, **opener_selections, **opener_raw_selections}

    df_filtered_opener_raw = user_specific_data.copy()
    for field, value in all_selections.items():
        if value and value != "All":  # "All" means no filter
            df_filtered_opener_raw = df_filtered_opener_raw[df_filtered_opener_raw[field] == value]

    st.dataframe(df_filtered_opener_raw)

# To do :
# 1. Clean the code to centralize ["opener_2_moves", "opener_4_moves", "opener_6_moves"]
# 2. Clean the table and sort by date