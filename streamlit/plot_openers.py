import streamlit as st
import pandas as pd
import plotly.express as px
from data_processing import get_player_opening_statistics, get_score_distribution_by_opening, min_benchmark_games
from typing import List

def render_opening_sunburst(
    df: pd.DataFrame, 
    last_n_games: int,
    list_dim: List[str]
) -> None:
    """
    Renders two Sunburst charts showing chess opening sequences and winrate:
    - Left: all games in the filtered dataset
    - Right: last N games
    """
    if df.empty:
        st.warning("No opening data available for the current filters.")
        return

    # Aggregate both datasets
    agg_all     = get_player_opening_statistics(df, list_dim)
    agg_recent  = get_player_opening_statistics(df, list_dim, last_n_games)

    # Layout: two columns
    col_all, col_recent = st.columns(2)

    # All games Sunburst
    with col_all:
        st.subheader(f"Winrate per opener - All games")
        fig_all = px.sunburst(
            agg_all,
            path=list_dim,
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
            path=list_dim,
            values="total_games",
            color="winrate",
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0.5,
            range_color=[0, 1],
            hover_data={"total_games": True, "winrate": ":.2%"}
        )
        fig_recent.update_layout(width=800, height=800, coloraxis_showscale=False)
        st.plotly_chart(fig_recent, use_container_width=True, key=f"sunburst_recent")


def render_score_progression(df: pd.DataFrame) -> None:
    """
    Renders one score-progression chart per opening (2-column grid),
    sorted by number of games descending.
    """
    st.subheader("Score distribution over moves")
    st.markdown(
        f"Distribution at each move (minimal boxplot), by opening. Only openings with at least **{min_benchmark_games}** games are shown."
    )

    if df.empty:
        st.warning("No data available for the selected filters.")
        return

    df_distribution = get_score_distribution_by_opening(
        df, opening_col="uci_hierarchy_level_7_name", min_games=min_benchmark_games
    )

    if df_distribution.empty:
        st.warning(f"No openings with at least {min_benchmark_games} games found for the selected filters.")
        return

    openings = df_distribution.groupby("opening")["n_games"].first().sort_values(ascending=False).index.tolist()
    turns = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
    color = "#1f77b4"
    median_color = "yellow"
    cols = st.columns(2)

    for i, opening in enumerate(openings):
        opening_data = df_distribution[df_distribution["opening"] == opening].copy()
        n_games = opening_data["n_games"].iloc[0]
        opening_data["turn_label"] = opening_data["turn"].astype(str)

        fig = px.box(
            opening_data,
            x="turn_label",
            y="score",
            points=False,
            category_orders={"turn_label": [str(t) for t in turns]},
        )

        fig.update_traces(
            line_color=color,
            fillcolor="rgba(31,119,180,0.08)",
            marker=dict(size=0),
            width=0.55,
            hovertemplate="Move: %{x}<br>Score: %{y:.3f}<extra></extra>",
        )

        median_by_turn = (
            opening_data.groupby("turn_label", as_index=False)["score"]
            .median()
            .rename(columns={"score": "median_score"})
        )
        median_by_turn["turn_label"] = pd.Categorical(
            median_by_turn["turn_label"],
            categories=[str(t) for t in turns],
            ordered=True,
        )
        median_by_turn = median_by_turn.sort_values("turn_label")

        fig.add_scatter(
            x=median_by_turn["turn_label"],
            y=median_by_turn["median_score"],
            mode="lines+markers",
            line=dict(color=median_color, width=2.5, shape="spline", smoothing=0.8),
            marker=dict(color=median_color, size=6, symbol="diamond"),
            name="Median",
            showlegend=False,
            hovertemplate="Move: %{x}<br>Median: %{y:.3f}<extra></extra>",
        )

        fig.update_layout(
            title=f"<b>{opening}</b> (n={n_games})",
            xaxis_title="Move Number",
            yaxis_title="Position Score",
            height=400,
            template="plotly",
            margin=dict(l=60, r=20, t=70, b=60),
            font=dict(size=9),
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            boxgap=0.35,
            boxgroupgap=0.15,
        )

        fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(size=9), type="category")
        fig.update_yaxes(showgrid=False, zeroline=False, tickfont=dict(size=9))
        fig.add_hline(y=0, line_dash="solid", line_color="rgba(100,100,100,0.3)", line_width=1.5)
        fig.add_annotation(
            text="Balanced", xref="paper", yref="y", x=1.02, y=0,
            showarrow=False, font=dict(size=9, color="rgba(100,100,100,0.6)"), xanchor="left"
        )

        with cols[i % 2]:
            st.plotly_chart(fig, use_container_width=True)