import streamlit as st
import pandas as pd
import plotly.express as px
from data_processing import get_player_opening_statistics

def render_opening_sunburst(df: pd.DataFrame, last_n_games: int = 30) -> None:
    """
    Renders two Sunburst charts showing chess opening sequences and winrate:
    - Left: all games in the filtered dataset
    - Right: last N games
    """
    if df.empty:
        st.warning("No opening data available for the current filters.")
        return

    # Aggregate both datasets
    agg_all     = get_player_opening_statistics(df)
    agg_recent  = get_player_opening_statistics(df, last_n_games)

    # Layout: two columns
    col_all, col_recent = st.columns(2)

    # All games Sunburst
    with col_all:
        st.subheader(f"Winrate per opener - All games")
        fig_all = px.sunburst(
            agg_all,
            path=["opener_2_moves", "opener_4_moves", "opener_6_moves"],
            values="total_games",
            color="winrate",
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0.5,
            range_color=[0, 1],
            hover_data={"total_games": True, "winrate": ":.2%"}
        )
        fig_all.update_layout(width=800, height=800, coloraxis_showscale=False)
        st.plotly_chart(fig_all, use_container_width=True, key=f"sunburst_all")

    # Last N games Sunburst
    with col_recent:
        st.subheader(f"Winrate per opener – Last {last_n_games} games")
        fig_recent = px.sunburst(
            agg_recent,
            path=["opener_2_moves", "opener_4_moves", "opener_6_moves"],
            values="total_games",
            color="winrate",
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0.5,
            range_color=[0, 1],
            hover_data={"total_games": True, "winrate": ":.2%"}
        )
        fig_recent.update_layout(width=800, height=800, coloraxis_showscale=False)
        st.plotly_chart(fig_recent, use_container_width=True, key=f"sunburst_recent")