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

def apply_filters(data: pd.DataFrame, filter_fields: list) -> pd.DataFrame:
    filters = {}
    for field in filter_fields:
        options = sorted(list(data[field].unique()))
        selected_option = st.sidebar.selectbox(f"Select {field.replace('_', ' ').title()}", options=options, index=0)
        filters[field] = selected_option

    filtered_data = data.copy()
    for field, value in filters.items():
        filtered_data = filtered_data[filtered_data[field] == value]

    return filtered_data

@st.cache_data
def get_player_aggregates(data: pd.DataFrame, agg_dict: dict) -> pd.DataFrame:
    agg_funcs = {k: v["agg"] for k, v in agg_dict.items()}
    filtered_data = data.groupby('username').filter(lambda x: len(x) >= 30)
    return filtered_data.groupby('username').agg(agg_funcs).reset_index()

def render_metric_boxplot(df: pd.DataFrame, metric: str, username_to_highlight: str, left_annotation: str, right_annotation: str):
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

# --- Load and filter data ---
df_filtered = apply_filters(get_raw_data(), ["playing_as", "time_class", "playing_result", "playing_rating_range"])

agg_dict = {
    'prct_time_remaining_mid': {
        'agg': 'median',
        'left_annotation': '⌛Slow',
        'right_annotation': '⚡Fast'
    },
    'nb_throw_playing': {
        'agg': 'mean',
        'left_annotation': '🎯Accurate',
        'right_annotation': '💥Confused'
    },
    'nb_throw_blunder_playing': {
        'agg': 'mean',
        'left_annotation': '🎯Accurate',
        'right_annotation': '💥Confused'
    },
    'nb_throw_massive_blunder_playing': {
        'agg': 'mean',
        'left_annotation': '🎯Accurate',
        'right_annotation': '💥Confused'
    },
    'nb_missed_opportunity_massive_blunder_playing': {
        'agg': 'mean',
        'left_annotation': '🔍Attentive',
        'right_annotation': '🙈Blind'
    },
}

# --- Aggregate ---
df_player_agg = get_player_aggregates(df_filtered, agg_dict)

# --- Define highlighted player ---
username_list = sorted(df_player_agg["username"].unique())

username_to_highlight = st.selectbox(
    "⭐ Select Username to Highlight",
    options = username_list,
    index   = username_list.index(st.session_state.get("selected_username", "Zundorn")),
    key     = "selected_username"
)

st.title("Chess.com BI Dashboard")

# --- Render Boxplots ---
for metric, config in agg_dict.items():
    render_metric_boxplot(
        df_player_agg,
        metric,
        username_to_highlight,
        left_annotation=config["left_annotation"],
        right_annotation=config["right_annotation"]
    )