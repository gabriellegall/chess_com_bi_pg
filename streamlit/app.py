# To do: remove the hard coded last 30 games
# To do: add the bullet chart on the winrate
# To do: add the audit trail for the statistics
# To do: add the customized message describing the performance

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data.loader import load_query
import numpy as np

st.set_page_config(layout="wide")

@st.cache_data
def get_raw_data():
    return load_query("data/agg_games_with_moves__games.sql")

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
    st.header("Game Filters")
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

def render_metric_boxplot(df: pd.DataFrame, metric: str, value_all: float, value_specific: float, left_annotation: str, right_annotation: str, plot_title: str, last_n_games: int):
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
        title=plot_title,
        labels={metric: metric.replace('_', ' ').title(), "category": ""},
        orientation='h'
    )

    # Highlight value_all
    if value_all is not None:
        fig.add_trace(go.Scatter(
            x=[value_all],
            y=['Player Distribution'], 
            mode="markers",
            marker=dict(color="yellowgreen", size=10, symbol="circle", line=dict(width=1, color='black')),
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
        height=250
    )

    # Annotate min/max
    x_min = df_plot[metric].min()
    x_max = df_plot[metric].max()
    fig.add_annotation(x=x_min, y=-0.4, text=left_annotation, showarrow=False, font=dict(color="white"))
    fig.add_annotation(x=x_max, y=-0.4, text=right_annotation, showarrow=False, font=dict(color="white"))

    st.plotly_chart(fig, use_container_width=True)

# --- Main Application ---

# Load initial data
raw_data = get_raw_data()
st.title("Chess.com Player Performance Benchmark")

# --- 1. Primary Player Selection ---
all_usernames = sorted(raw_data["username"].unique())
default_user = "Zundorn" if "Zundorn" in all_usernames else all_usernames[0]

selected_username = st.sidebar.selectbox(
    "⭐ Select a Player to Analyze",
    options=all_usernames,
    index=all_usernames.index(st.session_state.get("selected_username", default_user)),
    key="selected_username"
)

last_n_games = st.sidebar.slider(
    "Number of recent games to analyze",
    min_value=20,
    max_value=200,
    value=30,
    step=5,
    key="last_n_games"
)

# --- 2. Dependent Filters ---
user_specific_data = raw_data[raw_data['username'] == selected_username]

# Define filter fields for sidebar (pane) and main content area
filter_fields_pane = ["time_class", "playing_rating_range"]
filter_fields_main = ["playing_as", "playing_result"]

# Render filters and get selections from both locations
pane_selections = render_sidebar_filters(user_specific_data, filter_fields_pane)

# --- Win Rate Chart (affected by pane filters only) ---
st.header("Win Rate by Color")
df_pane_filtered = user_specific_data.copy()
for field, value in pane_selections.items():
    if value:
        df_pane_filtered = df_pane_filtered[df_pane_filtered[field] == value]

if df_pane_filtered.empty:
    st.warning("No data available for win rate chart with current sidebar filters.")
else:
    col1, col2 = st.columns(2)

    # Prepare data for aggregation
    df_win_rate_data = df_pane_filtered.copy()
    df_win_rate_data['is_win'] = (df_win_rate_data['playing_result'] == 'Win').astype(int)

    # Get win rate data using the updated function
    win_rate_data, win_rate_data_recent = get_player_metric_values(
        df_win_rate_data, 'is_win', selected_username, 'mean', last_n=last_n_games, aggregation_dimension='playing_as'
    )
    win_rate_data = win_rate_data.rename(columns={'is_win': 'win_rate'})
    win_rate_data_recent = win_rate_data_recent.rename(columns={'is_win': 'win_rate'})

    with col1:
        if win_rate_data.empty:
            st.warning("Not enough data to calculate overall win rate by color.")
        else:
            fig_win_rate = px.bar(
                win_rate_data,
                y='playing_as',
                x='win_rate',
                title="Overall Win Rate",
                labels={'playing_as': '', 'win_rate': 'Win Rate'},
                color='playing_as',
                color_discrete_map={'White': 'white', 'Black': 'grey'},
                orientation='h',
                text='win_rate'
            )
            fig_win_rate.update_traces(texttemplate='%{text:.0%}', textposition='inside')
            fig_win_rate.update_layout(
                xaxis=dict(visible=False),
                showlegend=False,
                height=300,
                yaxis=dict(showgrid=False)
            )
            st.plotly_chart(fig_win_rate, use_container_width=True)

    with col2:
        if win_rate_data_recent.empty:
             st.info(f"Not enough recent games for 'Last {last_n_games}' analysis with these filters.")
        else:
            fig_win_rate_last_n = px.bar(
                win_rate_data_recent,
                y='playing_as',
                x='win_rate',
                title=f"Last {last_n_games} Games Win Rate",
                labels={'playing_as': '', 'win_rate': 'Win Rate'},
                color='playing_as',
                color_discrete_map={'White': 'white', 'Black': 'grey'},
                orientation='h',
                text='win_rate'
            )
            fig_win_rate_last_n.update_traces(texttemplate='%{text:.0%}', textposition='inside')
            fig_win_rate_last_n.update_layout(
                xaxis=dict(visible=False),
                showlegend=False,
                height=300,
                yaxis=dict(showgrid=False)
            )
            st.plotly_chart(fig_win_rate_last_n, use_container_width=True)

st.divider()

main_selections = render_main_filters(user_specific_data, filter_fields_main)

# Combine all selections into a single dictionary
all_selections = {**pane_selections, **main_selections}

# Apply the combined filters to the entire dataset
df_filtered = raw_data.copy()
for field, value in all_selections.items():
    if value: # Ensure a selection was made
        df_filtered = df_filtered[df_filtered[field] == value]

# --- 3. Aggregate Data ---
# Define all metrics that will be plotted
agg_dict = {
    'prct_time_remaining_mid': {'agg': 'median', 'left_annotation': '⌛Slow', 'right_annotation': '⚡Fast', 'plot_title': 'Distribution of Time Remaining (Mid Game)'},
    'prct_time_remaining_late': {'agg': 'median', 'left_annotation': '⌛Slow', 'right_annotation': '⚡Fast', 'plot_title': 'Distribution of Time Remaining (Late Game)'},

    'nb_throw_blunder_playing': {'agg': 'mean', 'left_annotation': '🎯Accurate', 'right_annotation': '😬Confused', 'plot_title': '🟠 Small Throws'},
    'nb_throw_massive_blunder_playing': {'agg': 'mean', 'left_annotation': '🎯Accurate', 'right_annotation': '😬Confused', 'plot_title': '🔴 Massive Throws'},

    'nb_missed_opportunity_blunder_playing': {'agg': 'mean', 'left_annotation': '🔍Attentive', 'right_annotation': '🙈Blind', 'plot_title': '🟠 Small Missed Opportunities'},
    'nb_missed_opportunity_massive_blunder_playing': {'agg': 'mean', 'left_annotation': '🔍Attentive', 'right_annotation': '🙈Blind', 'plot_title': '🔴 Massive Missed Opportunities'},

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

# Define the pairs for side-by-side plotting: (Title, (left_metric, right_metric))
plot_pairs = [
    ("⏳ Time Management (mid-game vs. late-game)", ("prct_time_remaining_mid", "prct_time_remaining_late")),
    ("😬 Throws (small vs. massive)", ("nb_throw_blunder_playing", "nb_throw_massive_blunder_playing")),
    ("🙈 Missed Opportunities (small vs. massive)", ("nb_missed_opportunity_blunder_playing", "nb_missed_opportunity_massive_blunder_playing")),
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

    # Loop through the defined pairs to render graphs
    for title, (metric_left, metric_right) in plot_pairs:
        st.header(title)
        col1, col2 = st.columns(2)

        # For the left metric
        config_left = agg_dict[metric_left]
        value_all_left, value_specific_left = get_player_metric_values(
            df_filtered, metric_left, username_to_highlight, config_left['agg'], last_n=last_n_games
        )
        with col1:
            render_metric_boxplot(
                df_player_agg,
                metric_left,
                value_all=value_all_left,
                value_specific=value_specific_left,
                left_annotation=config_left["left_annotation"],
                right_annotation=config_left["right_annotation"],
                plot_title=config_left["plot_title"],
                last_n_games=last_n_games
            )

        # For the right metric
        config_right = agg_dict[metric_right]
        value_all_right, value_specific_right = get_player_metric_values(
            df_filtered, metric_right, username_to_highlight, config_right['agg'], last_n=last_n_games
        )
        with col2:
            render_metric_boxplot(
                df_player_agg,
                metric_right,
                value_all=value_all_right,
                value_specific=value_specific_right,
                left_annotation=config_right["left_annotation"],
                right_annotation=config_right["right_annotation"],
                plot_title=config_right["plot_title"],
                last_n_games=last_n_games
            )

        # Add toggle section for additional visuals (only for Throws and Missed Opportunities)
        if title in ["😬 Throws (small vs. massive)", "🙈 Missed Opportunities (small vs. massive)"]:
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
                        render_metric_boxplot(
                            df_player_agg,
                            metric,
                            value_all=value_all,
                            value_specific=value_specific,
                            left_annotation=config["left_annotation"],
                            right_annotation=config["right_annotation"],
                            plot_title=config["plot_title"],
                            last_n_games=last_n_games
                        )

                # Render additional metrics for the right column
                with col_right:
                    for metric in additional_metrics_right:
                        config = agg_dict[metric]
                        value_all, value_specific = get_player_metric_values(
                            df_filtered, metric, username_to_highlight, config['agg'], last_n=last_n_games
                        )
                        render_metric_boxplot(
                            df_player_agg,
                            metric,
                            value_all=value_all,
                            value_specific=value_specific,
                            left_annotation=config["left_annotation"],
                            right_annotation=config["right_annotation"],
                            plot_title=config["plot_title"],
                            last_n_games=last_n_games
                        )

        st.divider()