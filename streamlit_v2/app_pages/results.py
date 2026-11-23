"""Results & context: ELO trend, win rate by ELO matchup, recent progression.

Reads the global filters set by app.py from st.session_state.
"""
import pandas as pd
import streamlit as st

import charts
import cube
import period

filters: cube.Filters = st.session_state.filters
start, end, today = filters.start, filters.end, st.session_state.today
several_time_classes = st.session_state.several_time_classes
TC_HINT = cube.TC_HINT

# ---------- ELO trend ----------
with st.container(border=True):
    grain = "day" if (end - start).days <= 92 else "week"
    st.subheader("ELO trend by time class")
    st.caption(f"Context: am I improving? Average ELO per {grain}.")
    trend = cube.elo_trend(filters, grain)
    if trend.empty:
        st.info("No games match these filters.", icon=":material/filter_alt_off:")
    else:
        trend["period"] = pd.to_datetime(trend["period"])
        st.altair_chart(charts.elo_trend(trend, grain))

# ---------- ELO matrix ----------
with st.container(border=True):
    st.subheader("Win rate by player ELO and opponent ELO")
    st.caption(
        "Context: do I beat stronger players? Rows are 50-point bands of your rating, columns your opponent's. "
        "Squares right of the diagonal are stronger opponents. Square size = games, colour = win rate."
    )
    matrix_split = st.segmented_control(
        "Colour", ["All games", "Split by colour"], default="All games", key="matrix_split",
    ) == "Split by colour"
    if several_time_classes:
        st.warning(TC_HINT, icon=":material/info:")
    matrix = cube.elo_matrix(filters, matrix_split)
    if matrix.empty:
        st.info("No games match these filters.", icon=":material/filter_alt_off:")
    else:
        st.altair_chart(charts.elo_matrix(matrix, matrix_split), width="content")

# ---------- Progression ----------
with st.container(border=True):
    # The title reads the period control drawn just below it: Streamlit stores a widget's new value before the rerun.
    title_period = period.label(st.session_state.get("pg_days") or period.DEFAULT).lower()
    st.subheader(f"Progression: the {title_period} against the games before")
    st.caption("Lever: see against which opponents the work pays off. "
               "Each line runs from your win rate before (hollow grey dot) to the recent period (filled blue dot).")
    with st.container(horizontal=True, gap="large"):
        choice = period.control("pg_days")
        pg_split = st.segmented_control(
            "White vs Black", ["All games", "Split White / Black"], default="All games", key="pg_split",
        ) == "Split White / Black"
    recent_period = period.resolve(choice, filters, today)
    if recent_period.is_session and recent_period.session is None:
        st.stop()  # resolve() already says why; the progression is the last section of the page
    # A cutoff day, or the session: the games before it are the ones ended before the session started.
    split_point = recent_period.session or recent_period.cutoff
    split_label = (f"{recent_period.session.start:%d %b %Y %H:%M}" if recent_period.is_session
                   else f"{recent_period.cutoff:%d %b %Y}")

    summary = cube.progression_summary(filters, split_point)
    before, recent = summary.loc["before"], summary.loc["recent"]

    def delta(field: str, as_points: bool = False) -> str | None:
        """Recent minus before, as percentage points for a rate."""
        if pd.isna(before[field]) or pd.isna(recent[field]):
            return None
        diff = recent[field] - before[field]
        return f"{diff * 100:+.1f} pts" if as_points else f"{diff:+,.0f}"

    with st.container(horizontal=True):
        st.metric(f"Games, {recent_period.label.lower()}",f"{int(recent['games']):,}", border=True,
                  help=f"{int(before['games']):,} games before, from {start:%d %b %Y}.")
        st.metric("Win rate", "—" if pd.isna(recent["win_rate"]) else f"{recent['win_rate']:.1%}",
                  delta("win_rate", as_points=True), border=True, help="Wins ÷ (wins + losses), vs the games before.")
        st.metric("Average ELO", "—" if pd.isna(recent["avg_rating"]) else f"{recent['avg_rating']:,.0f}",
                  delta("avg_rating"), border=True)
        st.metric("Average opponent ELO", "—" if pd.isna(recent["avg_opponent_rating"]) else f"{recent['avg_opponent_rating']:,.0f}",
                  delta("avg_opponent_rating"), delta_color="off", border=True)

    if not before["games"]:
        st.info(
            f"No games before {split_label} in the selected dates, so there is nothing to compare with. "
            "Widen the game end date or shorten the recent period.",
            icon=":material/compare_arrows:",
        )

    gap = cube.progression(filters, split_point, "rating_gap_category", pg_split)
    band = cube.progression(filters, split_point, "opponent_rating_band", pg_split)
    if not band.empty:
        band["band"] = band["opponent_rating_band"].astype(int).map(lambda b: f"{b}–{b + 49}")
    gap_order = [g for g in cube.GAP_ORDER if not gap.empty and g in set(gap["rating_gap_category"])]
    band_order = [] if band.empty else [f"{b}–{b + 49}" for b in sorted(band["opponent_rating_band"].astype(int).unique(), reverse=True)]

    def max_games(df: pd.DataFrame) -> int:
        return int(max(df["before_games"].max(), df["recent_games"].max(), 1)) if not df.empty else 1

    progression_charts = [
        ("Win rate change by opponent strength",
         "One row per kind of opponent, compared with your rating at the time of each game: "
         "much weaker (> 50 below), weaker (16–50 below), similar (within 15), stronger (16–50 above), much stronger (> 50 above).",
         gap, "rating_gap_category", gap_order),
        ("Win rate change by opponent ELO band",
         "One row per 50-point band of your opponent's rating. A row with a single dot was only met in one period.",
         band, "band", band_order),
    ]

    def render_progression(title: str, note: str, df: pd.DataFrame, label: str, order: list[str]) -> None:
        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.caption(note)
            if label == "band" and several_time_classes:
                st.warning(TC_HINT, icon=":material/info:")
            if df.empty:
                st.info("No games match these filters.", icon=":material/filter_alt_off:")
                return
            if not pg_split:
                st.altair_chart(charts.dumbbell(df, label, order, max_games(df)))
                return
            # Split: White on the left, Black on the right, same rows and dot scale on both sides.
            left, right = st.columns(2, gap="large", border=False)
            for col, colour in ((left, "White"), (right, "Black")):
                with col:
                    side = df[df["playing_as"] == colour]
                    if side.empty:
                        st.info(f"No games with {colour}.")
                    else:
                        st.altair_chart(charts.dumbbell(side, label, order, max_games(df), title=f"Playing {colour}"))

    if pg_split:
        for spec in progression_charts:
            render_progression(*spec)
    else:
        for col, spec in zip(st.columns(2), progression_charts):
            with col:
                render_progression(*spec)
