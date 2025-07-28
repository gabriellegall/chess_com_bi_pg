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

def apply_dependent_filters(full_data: pd.DataFrame, dependent_data: pd.DataFrame, filter_fields: list) -> pd.DataFrame:
    """
    Creates sidebar filters. Filter options are based on 'dependent_data' (the selected user's games),
    but the filtering itself is applied to the 'full_data'.
    """
    st.sidebar.header("Game Filters")
    selections = {}

    for field in filter_fields:
        # Get available options from the data of the selected user
        options = sorted(list(dependent_data[field].unique()))
        
        if not options:
            st.sidebar.warning(f"No '{field.replace('_', ' ')}' options for this player.")
            continue
        
        # Create the selectbox in the sidebar
        selected_option = st.sidebar.selectbox(
            f"Select {field.replace('_', ' ').title()}", 
            options=options
        )
        selections[field] = selected_option

    # Apply the user's selections to the entire dataset
    filtered_data = full_data.copy()
    for field, value in selections.items():
        filtered_data = filtered_data[filtered_data[field] == value]

    return filtered_data

@st.cache_data
def get_player_aggregates(data: pd.DataFrame, agg_dict: dict) -> pd.DataFrame:
    agg_funcs = {k: v["agg"] for k, v in agg_dict.items()}
    filtered_data = data.groupby('username').filter(lambda x: len(x) >= 30)
    if filtered_data.empty:
        return pd.DataFrame()
    return filtered_data.groupby('username').agg(agg_funcs).reset_index()

def render_metric_boxplot(df: pd.DataFrame, metric: str, username_to_highlight: str, left_annotation: str, right_annotation: str):
    """Renders a boxplot for a given metric, highlighting a specific user."""
    df_plot = df.copy()
    df_plot['category'] = 'Player Distribution'

    highlight_value = df_plot.loc[df_plot["username"] == username_to_highlight, metric].iloc[0]

    fig = px.box(
        df_plot,
        x=metric,
        y="category",
        title=f"Distribution of {metric.replace('_', ' ').title()}",
        labels={metric: metric.replace('_', ' ').title(), "category": ""},
        orientation='h'
    )

    fig.add_trace(go.Scatter(
        x=[highlight_value],
        y=['Player Distribution'], 
        mode="markers",
        marker=dict(color="#ffde59", size=15, symbol="star", line=dict(width=1, color='black')),
        name=f"Highlight: {username_to_highlight}",
        showlegend=False
    ))

    fig.update_layout(
        yaxis=dict(title="", showticklabels=True), 
        xaxis_title=metric.replace('_', ' ').title(),
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
st.title("Chess.com BI Dashboard")

# --- 1. Primary Player Selection ---
all_usernames = sorted(raw_data["username"].unique())
default_user = "Zundorn" if "Zundorn" in all_usernames else all_usernames[0]

selected_username = st.selectbox(
    "⭐ Select a Player to Analyze",
    options=all_usernames,
    index=all_usernames.index(st.session_state.get("selected_username", default_user)),
    key="selected_username"
)

# --- 2. Dependent Sidebar Filters ---
user_specific_data = raw_data[raw_data['username'] == selected_username]
filter_fields = ["playing_as", "time_class", "playing_result", "playing_rating_range"]
df_filtered = apply_dependent_filters(raw_data, user_specific_data, filter_fields)

# --- 3. Aggregate Data ---
agg_dict = {
    'prct_time_remaining_mid': {'agg': 'median', 'left_annotation': '⌛Slow', 'right_annotation': '⚡Fast'},
    'nb_throw_playing': {'agg': 'mean', 'left_annotation': '🎯Accurate', 'right_annotation': '💥Confused'},
    'nb_throw_blunder_playing': {'agg': 'mean', 'left_annotation': '🎯Accurate', 'right_annotation': '💥Confused'},
    'nb_throw_massive_blunder_playing': {'agg': 'mean', 'left_annotation': '🎯Accurate', 'right_annotation': '💥Confused'},
    'nb_missed_opportunity_massive_blunder_playing': {'agg': 'mean', 'left_annotation': '🔍Attentive', 'right_annotation': '🙈Blind'},
}
df_player_agg = get_player_aggregates(df_filtered, agg_dict)

# --- 4. Render Plots ---
if df_player_agg.empty:
    st.warning("No player data available for the selected filters. Please adjust your selections.")
else:
    username_to_highlight = selected_username
    if username_to_highlight not in df_player_agg['username'].unique():
        st.warning(f"'{username_to_highlight}' has fewer than 30 games for these filters and cannot be shown. Highlighting the top player instead.")
        username_to_highlight = df_player_agg['username'].iloc[0]

    for metric, config in agg_dict.items():
        render_metric_boxplot(
            df_player_agg,
            metric,
            username_to_highlight,
            left_annotation=config["left_annotation"],
            right_annotation=config["right_annotation"]
        )