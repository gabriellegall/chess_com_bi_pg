import streamlit as st
import pandas as pd
import plotly.express as px
from data.loader import load_query


st.set_page_config(page_title="Chess DB Viewer", layout="wide")
st.title("Player Rating Over Time")

@st.cache_data
def load_data():
    return load_query("data/agg_games_with_moves__games.sql")

try:
    data = load_data()
    st.success("Connected to database successfully!")

    # Selector
    usernames       = sorted(data['username'].unique())
    time_classes    = sorted(data['time_class'].unique())
    selected_player     = st.selectbox("Select a player", usernames)
    selected_time_class = st.selectbox("Select a time class", time_classes)

    # Filter df
    data['end_time'] = pd.to_datetime(data['end_time'], errors='coerce')
    player_data = data[(data['username'] == selected_player) & (data['time_class'] == selected_time_class)]

    if player_data.empty:
        st.warning("No data found for the selected player.")
    else:
        st.subheader(f"Playing Rating Over Time for {selected_player}")

        fig = px.line(
            player_data.sort_values("end_time"),
            x="end_time",
            y="playing_rating",
            title=f"{selected_player}'s Playing Rating Progression",
            labels={
                "end_time": "Game End Time",
                "playing_rating": "Playing Rating"
            },
             render_mode="svg"
        )
        fig.update_layout(
            xaxis_title="End Time",
            yaxis_title="Playing Rating",
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Error loading data: {e}")
