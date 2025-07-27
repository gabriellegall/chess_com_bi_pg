# Bug to correct: switching to a different parameter resets the filter pane

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data.loader import load_query
import numpy as np

# --- Config ---
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
    return data.groupby('username').agg(agg_dict).reset_index()

def render_kpi_boxplot(df: pd.DataFrame, kpi: str, username_to_highlight: str):
    df_plot = df.copy()
    df_plot['category'] = 'Player Distribution'

    highlight_value = df_plot.loc[df_plot["username"] == username_to_highlight, kpi].iloc[0]

    fig = px.box(
        df_plot,
        x=kpi,
        y="category",
        title=f"Distribution of {kpi.replace('_', ' ').title()}",
        labels={kpi: kpi.replace('_', ' ').title(), "category": ""},
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
        xaxis_title=kpi.replace('_', ' ').title(),
        xaxis_tickformat=".0%",
        showlegend=True,
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(255,255,255,0.7)'),
        height=250
    )

    # Annotate min/max
    x_min = df_plot[kpi].min()
    x_max = df_plot[kpi].max()
    fig.add_annotation(x=x_min, y=-0.4, text="⌛Slow", showarrow=False, font=dict(color="white"))
    fig.add_annotation(x=x_max, y=-0.4, text="⚡Fast", showarrow=False, font=dict(color="white"))

    st.plotly_chart(fig, use_container_width=True)

# --- Load and filter data ---
df_filtered = apply_filters(get_raw_data(), ["playing_as", "time_class", "playing_result"])

agg_dict = {
    'prct_time_remaining_mid': 'median',
    'nb_throw_playing': 'mean',
    'nb_throw_blunder_playing': 'mean',
    'nb_throw_massive_blunder_playing': 'mean',
    'nb_missed_opportunity_massive_blunder_playing': 'mean',
}

# --- Aggregate ---
df_player_agg = get_player_aggregates(df_filtered, agg_dict)

# --- Highlight player ---
username_to_highlight = st.selectbox(
    "⭐ Select Username to Highlight", 
    options=sorted(df_player_agg["username"].unique()), 
    index=0
)

st.title("Chess.com BI Dashboard")

# --- Render Boxplots ---
for kpi in agg_dict:
    render_kpi_boxplot(df_player_agg, kpi, username_to_highlight)