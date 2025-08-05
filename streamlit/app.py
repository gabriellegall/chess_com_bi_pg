import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import yaml
from pathlib import Path
from config import get_metrics_config, get_plot_config
from data_processing import get_raw_data, get_players_aggregates, get_player_metric_values

st.set_page_config(layout="wide")

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
            
            selected_option = st.radio(
                f"Select {field.replace('_', ' ').title()}",
                options=options,
                horizontal=True,
                label_visibility="collapsed" # Hides the label above the radio buttons
            )
            selections[field] = selected_option
    return selections

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
        orientation='h',
        hover_data=['username']
    )

    # Replace the default box plot with one that has jittered points and better colors for dark theme
    fig.data[0].update(
        boxpoints='all', 
        jitter=0.3,
        pointpos=0,
        marker_color='rgba(0, 191, 255, 0.7)', 
        marker_size=5,
        fillcolor='rgba(0, 191, 255, 0.5)',
        line_color='rgba(0, 191, 255, 1)'
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
        height=200,
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

def render_plot_row(title, metrics, agg_dict, df_filtered, username_to_highlight, last_n_games, df_player_agg, help_text=None):
    """Renders a row of metric boxplots and their breakdowns."""
    st.subheader(title, help=help_text)

    metric_values = {}
    for metric in metrics:
        config = agg_dict[metric]
        value_all, value_specific = get_player_metric_values(
            df_filtered, metric, username_to_highlight, config['agg'], last_n=last_n_games
        )
        metric_values[metric] = {
            'config': config,
            'value_all': value_all,
            'value_specific': value_specific
        }

    # --- Boxplot Rendering ---
    cols = st.columns(len(metrics))
    for col, metric in zip(cols, metrics):
        with col:
            data = metric_values[metric]
            config = data['config']
            st.markdown(f"**{config['plot_title']}**", help=config.get('help'))
            render_metric_boxplot(
                df_player_agg,
                metric,
                value_all=data['value_all'],
                value_specific=data['value_specific'],
                left_annotation=config["left_annotation"],
                right_annotation=config["right_annotation"],
                last_n_games=last_n_games
            )

    # Add toggle section for additional visuals (only for Throws and Missed Opportunities)
    if title in ["💥 Throws (small vs. massive)", "👀 Missed Opportunities (small vs. massive)"]:
        with st.expander(f"Breakdown by game phase"):
            # This assumes the first two metrics are the main ones for the breakdown
            metric_left, metric_right = metrics[0], metrics[1]
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
agg_dict = get_metrics_config(game_phases_config, score_thresholds_config)

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
filter_fields_pane = ["time_control", "playing_rating_range"]
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
                st.markdown(f"<span style='color: yellow; font-size: 20px; font-weight: bold;'>|</span> Overall Games", unsafe_allow_html=True)
                st.metric("Total Games", f"{total_games}")
            with sub_col2:
                st.markdown(f"<span style='color: yellow; font-size: 20px; font-weight: bold;'>|</span> Overall Win Rate", unsafe_allow_html=True)
                st.metric(
                    "Overall Win Rate",
                    value=f"{win_rate_overall:.0f}%"
                )

            st.markdown("---")

            # Recent stats row
            sub_col3, sub_col4 = st.columns(2)
            with sub_col3:
                st.markdown(f"<span style='color: yellow;'>★</span> Recent Games (Last {last_n})", unsafe_allow_html=True)
                st.metric("Recent Games", f"{total_recent_games}")
            with sub_col4:
                delta_vs_overall = win_rate_recent - win_rate_overall
                st.markdown(f"<span style='color: yellow;'>★</span> Recent Win Rate", unsafe_allow_html=True)
                st.metric(
                    "Recent Win Rate",
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

    # --- 3. Aggregate Data ---
    # The agg_dict is now generated from config.py

    df_player_agg = get_players_aggregates(df_filtered, agg_dict)

    # Add explanatory text that will be updated as filters change.
    st.markdown(f"""
    In this section, we compare the performance of **{selected_username}** with other similar players (n={len(df_player_agg)}), holding constant: 
    - Color played: **{main_selections.get('playing_as', 'N/A')}**
    - Playing result: **{main_selections.get('playing_result', 'N/A')}**
    - Time control: **{pane_selections.get('time_control', 'N/A')}**
    - Rating range: **{pane_selections.get('playing_rating_range', 'N/A')}**
    """)

    # Define the pairs for side-by-side plotting from the config file
    plot_config = get_plot_config(game_phases_config, score_thresholds_config)

    # --- 4. Render Plots ---
    if df_player_agg.empty:
        st.warning("No player data available for the selected filters. Please adjust your selections.")
    else:
        username_to_highlight = selected_username
        if username_to_highlight not in df_player_agg['username'].unique():
            st.warning(f"'{username_to_highlight}' has fewer than 30 games for the selected filters and cannot be benchmarked. Please adjust the filters or select another player.")
        else:
            # Render the legend
            render_legend(username=username_to_highlight, last_n=last_n_games)

            # Loop through the defined pairs to render graphs
            for config_item in plot_config:
                title, metrics = config_item[0], config_item[1]
                # Default help text comes from the left metric's config in agg_dict
                help_text = agg_dict.get(metrics[0], {}).get('help')
                # If a specific help text is provided in the pair tuple, it overrides the default
                if len(config_item) > 2:
                    help_text = config_item[2]

                with st.container(border=True):
                    render_plot_row(
                        title, metrics, agg_dict, df_filtered, username_to_highlight, last_n_games, df_player_agg, help_text=help_text
                    )
