import streamlit as st

def render_summary_header(kpis: dict, last_n_games: int):
    """
    Renders a summary header with KPIs for White and Black from pre-calculated data.
    Displays the `last_n_games` information in the titles.
    """
    col1, col2 = st.columns(2)

    for color, data in kpis.items():
        if color not in ['White', 'Black']:
            continue

        container = col1 if color == 'White' else col2
        with container:
            emoji = "⚪" if color == "White" else "⚫"
            st.subheader(f"{emoji} Playing as {color}")
            
            if data is None:
                st.info(f"No games played as {color} with current filters.")
                continue

            # Overall stats row
            sub_col1, sub_col2 = st.columns(2)
            with sub_col1:
                st.markdown(f"<span style='color: yellow; font-size: 20px; font-weight: bold;'>|</span> Overall Games", unsafe_allow_html=True)
                st.metric("Total Games", f"{data['total_games']}")
            with sub_col2:
                st.markdown(f"<span style='color: yellow; font-size: 20px; font-weight: bold;'>|</span> Overall Win Rate", unsafe_allow_html=True)
                st.metric(
                    "Overall Win Rate",
                    value=f"{data['win_rate_overall']:.0f}%"
                )

            st.markdown("---")

            # Recent stats row
            sub_col3, sub_col4 = st.columns(2)
            with sub_col3:
                st.markdown(f"<span style='color: yellow;'>★</span> Recent Games (Last {last_n_games})", unsafe_allow_html=True)
                st.metric("Recent Games", f"{data['total_recent_games']}")
            with sub_col4:
                st.markdown(f"<span style='color: yellow;'>★</span> Recent Win Rate", unsafe_allow_html=True)
                st.metric(
                    "Recent Win Rate",
                    value=f"{data['win_rate_recent']:.0f}%",
                    delta=f"{data['delta_vs_overall']:.1f} pts vs overall",
                )

    # Add a checkbox at the bottom to show the raw data for recent games
    if st.checkbox(f"Show data for last {last_n_games} games"):
        st.dataframe(kpis['recent_games_df'], use_container_width=True)