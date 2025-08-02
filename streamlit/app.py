import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data.loader import load_query
import numpy as np
import yaml
from pathlib import Path

st.set_page_config(layout="wide")

@st.cache_data
def get_raw_data():
    return load_query("data/agg_games_with_moves__games.sql")

@st.cache_data
def load_dbt_project_config():
    """Loads the dbt_project.yml file."""
    # The CWD is the 'streamlit' folder, so we go up one level to the project root.
    project_root = Path.cwd().parent
    config_path = project_root / "dbt_project.yml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def render_sidebar_filters(dependent_data: pd.DataFrame, filter_fields: list) -> dict:
    """
    Creates select boxes in the sidebar for each field in `filter_fields`
    and returns the user's selections as a dictionary.
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
            options=options
        )
        selections[field] = selected_option
    return selections

def render_main_filters(dependent_data: pd.DataFrame, filter_fields: list) -> dict:
    """
    Creates select boxes in the main content area for each field in `filter_fields`,
    arranging them in columns, and returns the user's selections as a dictionary.
    """
    selections = {}
    
    # Create a number of columns equal to the number of filters
    cols = st.columns(len(filter_fields))
    
    # Iterate over the columns and fields simultaneously
    for col, field in zip(cols, filter_fields):
        with col:
            options = sorted(list(dependent_data[field].unique()))
            if not options:
                st.warning(f"No '{field.replace('_', ' ')}' options.")
                continue
            
            selected_option = st.selectbox(
                f"Select {field.replace('_', ' ').title()}",
                options=options
            )
            selections[field] = selected_option
    return selections

@st.cache_data
def get_players_aggregates(data: pd.DataFrame, agg_dict: dict, min_games: int = 30, group_by_col: str = 'username') -> pd.DataFrame:
    """
    This function aggregates the data for each player based on the provided aggregation dictionary.
    The dictionary should contain the metric names as keys and a the 'agg' key with the aggregation function (e.g., 'mean', 'median').
    Only groups with at least `min_games` will be returned.
    """
    agg_funcs = {k: v["agg"] for k, v in agg_dict.items()}
    filtered_data = data.groupby(group_by_col).filter(lambda x: len(x) >= min_games)
    
    if filtered_data.empty:
        return pd.DataFrame()
    
    return filtered_data.groupby(group_by_col).agg(agg_funcs).reset_index()

def get_player_metric_values(data: pd.DataFrame, metric: str, username: str, agg_type: str, last_n: int, aggregation_dimension: str = None) -> tuple | pd.DataFrame:
    """
    This function aggregates the metric for a specific user.
    If `aggregation_dimension` is None, it returns two scalar values as a tuple:
    - value_all: The aggregated value for the entire dataset for that user.
    - value_specific: The aggregated value for the last `last_n` games for that user.
    If `aggregation_dimension` is provided, it returns two DataFrames, one for all games and one for recent games,
    with the metric aggregated by the specified dimension.
    """
    user_data = data[data['username'] == username]
    if user_data.empty:
        return (None, None) if not aggregation_dimension else (pd.DataFrame(), pd.DataFrame())

    # Aggregation for all data
    if aggregation_dimension:
        value_all = user_data.groupby(aggregation_dimension).agg({metric: agg_type}).reset_index()
    else:
        if hasattr(user_data[metric], agg_type):
            value_all = getattr(user_data[metric], agg_type)()
        else:
            raise ValueError(f"Unsupported aggregation type: {agg_type}")

    # Aggregation for recent data
    user_data_sorted = user_data.sort_values('end_time', ascending=False)
    recent_data = user_data_sorted.head(last_n)
    
    if recent_data.empty:
        value_specific = None if not aggregation_dimension else pd.DataFrame()
    else:
        if aggregation_dimension:
            value_specific = recent_data.groupby(aggregation_dimension).agg({metric: agg_type}).reset_index()
        else:
            if hasattr(recent_data[metric], agg_type):
                value_specific = getattr(recent_data[metric], agg_type)()
            else:
                raise ValueError(f"Unsupported aggregation type: {agg_type}")

    return value_all, value_specific

def render_metric_boxplot(df: pd.DataFrame, metric: str, value_all: float, value_specific: float, left_annotation: str, right_annotation: str, last_n_games: int):
    """
    This function renders a boxplot for all players, and highlights two hard-coded values:
    - value_all 
    - value_specific
    It also takes care of the annotations for the min and max values on the x-axis.
    """
    df_plot = df.copy()
    df_plot['category'] = 'Player Distribution'

    fig = px.box(
        df_plot,
        x=metric,
        y="category",
        labels={metric: metric.replace('_', ' ').title(), "category": ""},
        orientation='h'
    )

    # Highlight value_all
    if value_all is not None:
        fig.add_trace(go.Scatter(
            x=[value_all],
            y=['Player Distribution'], 
            mode="markers",
            marker=dict(color="yellow", size=20, symbol="line-ns", line=dict(width=3, color='yellow')),
            name="Overall",
            showlegend=False
        ))
    
    # Highlight value_specific
    if value_specific is not None:
        fig.add_trace(go.Scatter(
            x=[value_specific],
            y=['Player Distribution'],
            mode="markers",
            marker=dict(color="yellow", size=15, symbol="star", line=dict(width=1, color='black')),
            name=f"Last {last_n_games} Games",
            showlegend=False
        ))

    fig.update_layout(
        yaxis=dict(title="", showticklabels=False),  # Hide Y-axis title and tick labels
        xaxis_title="",  # Keep X-axis title empty
        xaxis_tickformat=".0%",
        showlegend=True,
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(255,255,255,0.7)'),
        height=250,
        title=dict(text="") # Ensure title is empty
    )

    # Annotate min/max
    x_min = df_plot[metric].min()
    x_max = df_plot[metric].max()
    fig.add_annotation(x=x_min, y=-0.4, text=left_annotation, showarrow=False, font=dict(color="white"))
    fig.add_annotation(x=x_max, y=-0.4, text=right_annotation, showarrow=False, font=dict(color="white"))

    st.plotly_chart(fig, use_container_width=True)

def render_legend(username, last_n):
    """Renders a custom legend for the plot markers."""
    legend_html = f"""
    <div style="display: flex; align-items: center; justify-content: flex-start; gap: 25px; font-size: 14px; padding: 1px 0 1px 15px; margin-bottom: 15px;">
        <span style="font-weight: bold;">Legend:</span>
        <div style="display: flex; align-items: center;">
            <span style="color: yellow; font-size: 25px; font-weight: bold; margin-right: 8px;">|</span>
            <span>All games by {username}</span>
        </div>
        <div style="display: flex; align-items: center;">
            <span style="color: yellow; font-size: 20px; margin-right: 8px;">★</span>
            <span>Last {last_n} games by {username}</span>
        </div>
    </div>
    """
    st.markdown(legend_html, unsafe_allow_html=True)

def render_plot_pair(title, metric_left, metric_right, agg_dict, df_filtered, username_to_highlight, last_n_games, df_player_agg, help_text=None):
    """Renders a pair of metric boxplots and their breakdowns."""
    st.subheader(title, help=help_text)

    # For the left metric
    config_left = agg_dict[metric_left]
    value_all_left, value_specific_left = get_player_metric_values(
        df_filtered, metric_left, username_to_highlight, config_left['agg'], last_n=last_n_games
    )

    # For the right metric
    config_right = agg_dict[metric_right]
    value_all_right, value_specific_right = get_player_metric_values(
        df_filtered, metric_right, username_to_highlight, config_right['agg'], last_n=last_n_games
    )

    # --- Boxplot Rendering ---
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**{config_left['plot_title']}**", help=config_left.get('help'))
        render_metric_boxplot(
            df_player_agg,
            metric_left,
            value_all=value_all_left,
            value_specific=value_specific_left,
            left_annotation=config_left["left_annotation"],
            right_annotation=config_left["right_annotation"],
            last_n_games=last_n_games
        )

    with col2:
        st.markdown(f"**{config_right['plot_title']}**", help=config_right.get('help'))
        render_metric_boxplot(
            df_player_agg,
            metric_right,
            value_all=value_all_right,
            value_specific=value_specific_right,
            left_annotation=config_right["left_annotation"],
            right_annotation=config_right["right_annotation"],
            last_n_games=last_n_games
        )

    # Add toggle section for additional visuals (only for Throws and Missed Opportunities)
    if title in ["💥 Throws (small vs. massive)", "👀 Missed Opportunities (small vs. massive)"]:
        with st.expander(f"Breakdown by game phase"):
            additional_metrics_left = [
                f"{metric_left}_early", f"{metric_left}_mid", f"{metric_left}_late"
            ]
            additional_metrics_right = [
                f"{metric_right}_early", f"{metric_right}_mid", f"{metric_right}_late"
            ]

            col_left, col_right = st.columns(2)

            # Render additional metrics for the left column
            with col_left:
                for metric in additional_metrics_left:
                    config = agg_dict[metric]
                    value_all, value_specific = get_player_metric_values(
                        df_filtered, metric, username_to_highlight, config['agg'], last_n=last_n_games
                    )
                    st.markdown(f"**{config['plot_title']}**", help=config.get('help'))
                    render_metric_boxplot(
                        df_player_agg,
                        metric,
                        value_all=value_all,
                        value_specific=value_specific,
                        left_annotation=config["left_annotation"],
                        right_annotation=config["right_annotation"],
                        last_n_games=last_n_games
                    )

            # Render additional metrics for the right column
            with col_right:
                for metric in additional_metrics_right:
                    config = agg_dict[metric]
                    value_all, value_specific = get_player_metric_values(
                        df_filtered, metric, username_to_highlight, config['agg'], last_n=last_n_games
                    )
                    st.markdown(f"**{config['plot_title']}**", help=config.get('help'))
                    render_metric_boxplot(
                        df_player_agg,
                        metric,
                        value_all=value_all,
                        value_specific=value_specific,
                        left_annotation=config["left_annotation"],
                        right_annotation=config["right_annotation"],
                        last_n_games=last_n_games
                    )

# --- Main Application ---

# Load initial data
raw_data = get_raw_data()
dbt_config = load_dbt_project_config()
game_phases_config = dbt_config.get("vars", {}).get("game_phases", {})
score_thresholds_config = dbt_config.get("vars", {}).get("score_thresholds", {})

st.title("Chess.com Player Performance Benchmark")

# --- 1. Primary Player Selection ---
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

# --- 2. Dependent Filters ---
user_specific_data = raw_data[raw_data['username'] == selected_username]

# Define filter fields for sidebar (pane) and main content area
filter_fields_pane = ["time_class", "playing_rating_range"]
filter_fields_main = ["playing_as", "playing_result"]

# Render filters and get selections from both locations
pane_selections = render_sidebar_filters(user_specific_data, filter_fields_pane)

def calculate_win_loss_draw(df: pd.DataFrame) -> pd.DataFrame:
    """Adds is_win, is_loss, is_draw columns to the DataFrame."""
    df['is_win'] = (df['playing_result'] == 'Win').astype(int)
    df['is_loss'] = (df['playing_result'] == 'Loss').astype(int)
    df['is_draw'] = (df['playing_result'] == 'Draw').astype(int)
    return df

def render_summary_header(df: pd.DataFrame, last_n: int, username: str):
    """Renders a summary header with KPIs and gauges for White and Black pieces."""
    
    # Calculate win rates using the same function as the bar charts for consistency
    win_rate_data, win_rate_data_recent = get_player_metric_values(
        df, 'is_win', username, 'mean', last_n=last_n, aggregation_dimension='playing_as'
    )

    # Identify the last N games overall for the user with current filters
    recent_games_overall = df.sort_values('end_time', ascending=False).head(last_n)

    df_white = df[df['playing_as'] == 'White']
    df_black = df[df['playing_as'] == 'Black']

    col1, col2 = st.columns(2)

    for color, data in [('White', df_white), ('Black', df_black)]:
        container = col1 if color == 'White' else col2
        with container:
            emoji = "⚪" if color == "White" else "⚫"
            st.subheader(f"{emoji} Playing as {color}")
            
            if data.empty:
                st.info(f"No games played as {color} with current filters.")
                continue

            # Overall stats
            total_games = len(data)
            
            # Recent stats: count how many of the overall recent games were played with this color
            total_recent_games = len(recent_games_overall[recent_games_overall['playing_as'] == color])

            # Get win rates from pre-calculated dataframes
            wr_overall_series = win_rate_data[win_rate_data['playing_as'] == color]['is_win']
            win_rate_overall = wr_overall_series.iloc[0] * 100 if not wr_overall_series.empty else 0

            wr_recent_series = win_rate_data_recent[win_rate_data_recent['playing_as'] == color]['is_win']
            win_rate_recent = wr_recent_series.iloc[0] * 100 if not wr_recent_series.empty else 0

            # --- Display Metrics & Gauges ---
            # Overall stats row
            sub_col1, sub_col2 = st.columns(2)
            with sub_col1:
                st.metric("Total Games", f"{total_games}")
            with sub_col2:
                st.metric(
                    label="Overall Win Rate",
                    value=f"{win_rate_overall:.0f}%"
                )

            st.markdown("---")

            # Recent stats row
            sub_col3, sub_col4 = st.columns(2)
            with sub_col3:
                st.metric(f"Recent Games (Last {last_n})", f"{total_recent_games}")
            with sub_col4:
                delta_vs_overall = win_rate_recent - win_rate_overall
                st.metric(
                    label="Recent Win Rate",
                    value=f"{win_rate_recent:.0f}%",
                    delta=f"{delta_vs_overall:.1f} pts vs overall",
                )

    # Add a checkbox at the bottom to show the raw data for recent games
    if st.checkbox(f"Show data for last {last_n} games"):
        st.dataframe(recent_games_overall, use_container_width=True)


# Apply filters and render the summary header
df_pane_filtered = user_specific_data.copy()
for field, value in pane_selections.items():
    if value:
        df_pane_filtered = df_pane_filtered[df_pane_filtered[field] == value]

if df_pane_filtered.empty:
    st.warning("No data available for the selected filters.")
else:
    with st.container(border=True):
        st.header(f"How is {selected_username} performing?")
        df_pane_filtered = calculate_win_loss_draw(df_pane_filtered)
        render_summary_header(df_pane_filtered, last_n_games, selected_username)

with st.container(border=True):
    st.header(f"How does {selected_username} compare to other similar players?")
    
    main_selections = render_main_filters(user_specific_data, filter_fields_main)

    # Combine all selections into a single dictionary
    all_selections = {**pane_selections, **main_selections}

    # Apply the combined filters to the entire dataset
    df_filtered = raw_data.copy()
    for field, value in all_selections.items():
        if value:  # Ensure a selection was made
            df_filtered = df_filtered[df_filtered[field] == value]

    # Add explanatory text that will be updated as filters change.
    st.markdown(f"""
    In this section, we compare the performance of **{selected_username}** with other similar players, holding constant: 
    - Color played: **{main_selections.get('playing_as', 'N/A')}**
    - Playing result: **{main_selections.get('playing_result', 'N/A')}**
    - Time class: **{pane_selections.get('time_class', 'N/A')}**
    - Rating range: **{pane_selections.get('playing_rating_range', 'N/A')}**
    """)

    # --- 3. Aggregate Data ---
    # Define all metrics that will be plotted
    agg_dict = {
        'prct_time_remaining_mid': {'agg': 'median', 'left_annotation': '⌛Slow', 'right_annotation': '⚡Fast', 'plot_title': 'Percent of time remaining (mid game)'},
        'prct_time_remaining_late': {'agg': 'median', 'left_annotation': '⌛Slow', 'right_annotation': '⚡Fast', 'plot_title': 'Percentage of time remaining (late game)'},

        'nb_throw_blunder_playing': {'agg': 'mean', 'left_annotation': '🎯Accurate', 'right_annotation': '💥Confused', 'plot_title': '🟠 Small Throws', 'help': f"A 'Blunder' is any score variance decrease between {score_thresholds_config.get('variance_score_blunder')} and {score_thresholds_config.get('variance_score_massive_blunder')} centipawns."},
        'nb_throw_massive_blunder_playing': {'agg': 'mean', 'left_annotation': '🎯Accurate', 'right_annotation': '💥Confused', 'plot_title': '🔴 Massive Throws', 'help': f"A 'Massive Blunder' is any score variance decrease beyond {score_thresholds_config.get('variance_score_massive_blunder')} centipawns."},

        'nb_missed_opportunity_blunder_playing': {'agg': 'mean', 'left_annotation': '🔍Attentive', 'right_annotation': '👀Blind', 'plot_title': '🟠 Small Missed Opportunities', 'help': f"A 'Blunder' is any score variance decrease between {score_thresholds_config.get('variance_score_blunder')} and {score_thresholds_config.get('variance_score_massive_blunder')} centipawns."},
        'nb_missed_opportunity_massive_blunder_playing': {'agg': 'mean', 'left_annotation': '🔍Attentive', 'right_annotation': '👀Blind', 'plot_title': '🔴 Massive Missed Opportunities', 'help': f"A 'Massive Blunder' is any score variance decrease beyond {score_thresholds_config.get('variance_score_massive_blunder')} centipawns."},

        'nb_missed_opportunity_massive_blunder_playing_early': {'agg': 'mean', 'left_annotation': 'Short Games', 'right_annotation': 'Long Games', 'plot_title': '🔴 Massive Missed Opportunities - Early'},
        'nb_missed_opportunity_massive_blunder_playing_mid': {'agg': 'mean', 'left_annotation': 'Short Games', 'right_annotation': 'Long Games', 'plot_title': '🔴 Massive Missed Opportunities - Mid'},
        'nb_missed_opportunity_massive_blunder_playing_late': {'agg': 'mean', 'left_annotation': 'Short Games', 'right_annotation': 'Long Games', 'plot_title': '🔴 Massive Missed Opportunities - Late'},
        'nb_throw_massive_blunder_playing_early': {'agg': 'mean', 'left_annotation': 'Short Games', 'right_annotation': 'Long Games', 'plot_title': '🔴 Massive Throws - Early'},
        'nb_throw_massive_blunder_playing_mid': {'agg': 'mean', 'left_annotation': 'Short Games', 'right_annotation': 'Long Games', 'plot_title': '🔴 Massive Throws - Mid'},
        'nb_throw_massive_blunder_playing_late': {'agg': 'mean', 'left_annotation': 'Short Games', 'right_annotation': 'Long Games', 'plot_title': '🔴 Massive Throws - Late'},

        'nb_missed_opportunity_blunder_playing_early': {'agg': 'mean', 'left_annotation': 'Short Games', 'right_annotation': 'Long Games', 'plot_title': '🟠 Small Missed Opportunities - Early'},
        'nb_missed_opportunity_blunder_playing_mid': {'agg': 'mean', 'left_annotation': 'Short Games', 'right_annotation': 'Long Games', 'plot_title': '🟠 Small Missed Opportunities - Mid'},
        'nb_missed_opportunity_blunder_playing_late': {'agg': 'mean', 'left_annotation': 'Short Games', 'right_annotation': 'Long Games', 'plot_title': '🟠 Small Missed Opportunities - Late'},
        'nb_throw_blunder_playing_early': {'agg': 'mean', 'left_annotation': 'Short Games', 'right_annotation': 'Long Games', 'plot_title': '🟠 Small Throws - Early'},
        'nb_throw_blunder_playing_mid': {'agg': 'mean', 'left_annotation': 'Short Games', 'right_annotation': 'Long Games', 'plot_title': '🟠 Small Throws - Mid'},
        'nb_throw_blunder_playing_late': {'agg': 'mean', 'left_annotation': 'Short Games', 'right_annotation': 'Long Games', 'plot_title': '🟠 Small Throws - Late'},
    }

    # Define the pairs for side-by-side plotting: (Title, (left_metric, right_metric), optional_help_text)
    plot_pairs = [
        (
            "⏳ Time Management (mid-game vs. late-game)",
            ("prct_time_remaining_mid", "prct_time_remaining_late"),
            f"Time management is estimated looking at the percentage of time remaining on the clock at specific turns. For the mid-game: turn {game_phases_config.get('mid', {}).get('end_game_move')}, and for the late-game: turn {game_phases_config.get('late', {}).get('end_game_move')}."
        ),
        (
            "💥 Throws (small vs. massive)", 
            ("nb_throw_blunder_playing", "nb_throw_massive_blunder_playing"),
                            f"A throw is defined as a move which significantly worsens the player's position, **starting from a relatively even or disadvantageous position.** This means the engine evaluation was <= +{score_thresholds_config.get('even_score_limit')} centipawns before the move."
        ),
        (
            "👀 Missed Opportunities (small vs. massive)", 
            ("nb_missed_opportunity_blunder_playing", "nb_missed_opportunity_massive_blunder_playing"),
                            f"A missed opportunity is defined as a move which significantly worsens the player's position, **starting from an advantageous position.** This means the engine evaluation was > +{score_thresholds_config.get('even_score_limit')} centipawns before the move."
        ),
    ]

    df_player_agg = get_players_aggregates(df_filtered, agg_dict)

    # --- 4. Render Plots ---
    if df_player_agg.empty:
        st.warning("No player data available for the selected filters. Please adjust your selections.")
    else:
        username_to_highlight = selected_username
        if username_to_highlight not in df_player_agg['username'].unique():
            st.warning(f"'{username_to_highlight}' has fewer than {last_n_games} games for these filters and cannot be shown. Highlighting the top player instead.")
            username_to_highlight = df_player_agg['username'].iloc[0]

        # Render the legend
        render_legend(username=username_to_highlight, last_n=last_n_games)

        # Loop through the defined pairs to render graphs
        for pair in plot_pairs:
            title, (metric_left, metric_right) = pair[0], pair[1]
            # Default help text comes from the left metric's config in agg_dict
            help_text = agg_dict.get(metric_left, {}).get('help')
            # If a specific help text is provided in the pair tuple, it overrides the default
            if len(pair) > 2:
                help_text = pair[2]

            with st.container(border=True):
                render_plot_pair(
                    title, metric_left, metric_right, agg_dict, df_filtered, username_to_highlight, last_n_games, df_player_agg, help_text=help_text
                )
