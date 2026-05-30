import streamlit as st
import pandas as pd

from data_processing import get_players_aggregates
from plot_benchmark import render_legend, prepare_section_plot_data, render_plot_section
from plot_openers import render_opening_sunburst, render_score_progression
from ui_filters import apply_filters, render_page_filters


def render_benchmark_section(
    raw_data: pd.DataFrame,
    selected_username: str,
    last_n_games: int,
    sidebar_selections: dict,
    benchmark_selections: dict,
    section_config: list,
    plot_config: dict,
    min_benchmark_games: int,
) -> None:
    with st.container(border=True):
        st.header(f"How does {selected_username} compare to other similar players?")

        all_selections = {**sidebar_selections, **benchmark_selections}

        df_filtered_benchmark = raw_data.copy()
        df_filtered_benchmark = apply_filters(df_filtered_benchmark, all_selections)

        df_player_agg = get_players_aggregates(
            df_filtered_benchmark,
            plot_config,
            min_games=min_benchmark_games,
        )

        st.markdown(
            f"""
            In this section, we compare the performance of **{selected_username}** with other similar players having played at least **{min_benchmark_games}** games (n={len(df_player_agg)}), holding constant: 
            - Color played: **{benchmark_selections.get('playing_as', 'N/A')}**
            - Playing result: **{benchmark_selections.get('playing_result', 'N/A')}**
            - Time control: **{sidebar_selections.get('time_control', 'N/A')}**
            - Rating range: **{sidebar_selections.get('playing_rating_range', 'N/A')}**
            """
        )

        if st.checkbox("Show player details", key="show_benchmark_players"):
            player_counts = (
                df_filtered_benchmark["username_global"]
                .value_counts()
                .rename_axis("username_global")
                .reset_index(name="n_games")
                .loc[lambda d: d["n_games"] >= min_benchmark_games]
            )
            st.dataframe(player_counts)

        if df_player_agg.empty:
            st.warning("No player data available for the selected filters. Please adjust your selections.")
            return

        if selected_username not in df_player_agg["username_global"].unique():
            st.warning(
                f"'{selected_username}' has fewer than {min_benchmark_games} games for the selected filters and cannot be benchmarked. "
                "Please adjust the filters or select another player."
            )
            return

        render_legend(username=selected_username, last_n_games=last_n_games)
        all_section_plot_data = prepare_section_plot_data(
            section_config, plot_config, df_filtered_benchmark, selected_username, last_n_games
        )

        for prepared_section_data in all_section_plot_data:
            with st.container(border=True):
                render_plot_section(prepared_section_data, df_player_agg, last_n_games)


def render_opening_analysis_section(
    user_specific_data: pd.DataFrame,
    selected_username: str,
    last_n_games: int,
    sidebar_selections: dict,
    opener_selections: dict,
    list_dim: list,
) -> None:
    with st.container(border=True):
        st.header(f"How does {selected_username} perform on the various openers?")
        st.markdown("In this section, we explore the win rate on the various openings played:")

        all_selections = {**sidebar_selections, **opener_selections}

        df_filtered_opener = user_specific_data.copy()
        df_filtered_opener = apply_filters(df_filtered_opener, all_selections)

        render_opening_sunburst(df_filtered_opener, last_n_games=last_n_games, list_dim=list_dim)
        render_score_progression(df_filtered_opener)

        st.subheader("Raw data")

        opener_raw_selections = render_page_filters(
            user_specific_data, list_dim, context="opener_raw", style="dropdown", add_all=True
        )

        all_selections = {**sidebar_selections, **opener_selections, **opener_raw_selections}

        df_filtered_opener_raw = user_specific_data.copy()
        df_filtered_opener_raw = apply_filters(df_filtered_opener_raw, all_selections)

        st.dataframe(df_filtered_opener_raw)
