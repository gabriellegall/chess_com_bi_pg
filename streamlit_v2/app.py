"""Chess improvement: Results & context (v2).

Run from the repository root: streamlit run streamlit_v2/app.py
Data: Cube SQL API (view v_games); every filter is applied by Cube.
"""
from datetime import date, timedelta

import pandas as pd
import streamlit as st

import charts
import cube

st.set_page_config(page_title="Chess improvement", page_icon=":material/chess:", layout="wide")

st.title("What should I work on to win more?")
st.caption("Results & context · every figure is a Cube measure of the view `v_games`, filtered by Cube.")

# ---------- Filters header ----------
players = cube.players()
if players.empty:
    st.error("Cube returned no players. Check that Cube is running and the SQL API credentials in `.env` are set.")
    st.stop()

today = date.today()
PERIODS = {"Last month": 1, "Last 3 months": 3, "Last 6 months": 6, "Last 12 months": 12, "All games": None, "Custom range": "custom"}

with st.container(border=True):
    c_player, c_tc, c_elo, c_opp, c_date = st.columns([1.2, 1.3, 1.2, 1.2, 1.3], gap="medium")

    with c_player:
        player = st.selectbox(
            "Player",
            players["username_global"].tolist(),
            format_func=lambda u: f"{u} ({int(players.set_index('username_global').at[u, 'games']):,} games)",
            key="player",
        )

    profile = cube.player_profile(player)
    profile["day"] = pd.to_datetime(profile["day"]).dt.date
    first_day = profile["day"].min()

    def rating_bounds(col: str, tcs: list[str]) -> tuple[int, int]:
        """Slider bounds: the rating bands met in the selected time classes (all of them when none is picked)."""
        rows = profile[profile["time_class"].isin(tcs)] if tcs else profile
        lo, hi = int(rows[col].min()), int(rows[col].max()) + 50
        return lo, max(hi, lo + 50)

    with c_tc:
        tc_options = [t for t in charts.TIME_CLASS_COLOURS if t in set(profile["time_class"])]
        time_classes = st.pills(
            "Time class", tc_options, selection_mode="multi", format_func=str.capitalize,
            key=f"tc_{player}", help="Leave empty to include every time class.",
        )

    # The sliders reset when the player or the time classes change, since their bounds change too.
    slider_scope = f"{player}_{'-'.join(sorted(time_classes or []))}"
    with c_elo:
        elo_min, elo_max = rating_bounds("playing_rating_band", time_classes)
        elo = st.slider("Player ELO", elo_min, elo_max, (elo_min, elo_max), step=25, key=f"elo_{slider_scope}")

    with c_opp:
        opp_min, opp_max = rating_bounds("opponent_rating_band", time_classes)
        opp_elo = st.slider("Opponent ELO", opp_min, opp_max, (opp_min, opp_max), step=25, key=f"opp_{slider_scope}")

    with c_date:
        preset = st.selectbox("Game end date", list(PERIODS), index=3, key="period")
        months = PERIODS[preset]
        if months == "custom":
            picked = st.date_input("From / to", (first_day, today), min_value=first_day, max_value=today,
                                   key=f"dates_{player}", label_visibility="collapsed")
            start, end = (picked[0], picked[1]) if len(picked) == 2 else (picked[0] if picked else first_day, today)
        elif months is None:
            start, end = first_day, today
        else:
            start, end = (pd.Timestamp(today) - pd.DateOffset(months=months)).date(), today
        st.caption(f"{start:%d %b %Y} – {end:%d %b %Y}")

filters = cube.Filters(
    player=player,
    time_classes=tuple(time_classes or ()),
    elo=(int(elo[0]), int(elo[1])),
    opp_elo=(int(opp_elo[0]), int(opp_elo[1])),
    start=start,
    end=end,
)
several_time_classes = len(time_classes or tc_options) > 1
TC_HINT = "Several time classes are selected and their rating scales differ a lot. Pick one time class for a clean reading."

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
    st.subheader(f"Progression: the last {st.session_state.get('pg_days') or 90} days against the games before")
    st.caption("Lever: see against which opponents the work pays off. "
               "Each line runs from your win rate before (hollow grey dot) to the recent period (filled blue dot).")
    with st.container(horizontal=True, gap="large"):
        days = st.segmented_control(
            "Recent period", [30, 60, 90, 180], default=90, format_func=lambda d: f"Last {d} days", key="pg_days",
        ) or 90
        pg_split = st.segmented_control(
            "White vs Black", ["All games", "Split White / Black"], default="All games", key="pg_split",
        ) == "Split White / Black"

    cutoff = today - timedelta(days=days)
    summary = cube.progression_summary(filters, cutoff)
    before, recent = summary.loc["before"], summary.loc["recent"]

    def delta(field: str, as_points: bool = False) -> str | None:
        """Recent minus before, as percentage points for a rate."""
        if pd.isna(before[field]) or pd.isna(recent[field]):
            return None
        diff = recent[field] - before[field]
        return f"{diff * 100:+.1f} pts" if as_points else f"{diff:+,.0f}"

    with st.container(horizontal=True):
        st.metric(f"Games, last {days} days", f"{int(recent['games']):,}", border=True,
                  help=f"{int(before['games']):,} games before, from {start:%d %b %Y}.")
        st.metric("Win rate", "—" if pd.isna(recent["win_rate"]) else f"{recent['win_rate']:.1%}",
                  delta("win_rate", as_points=True), border=True, help="Wins ÷ (wins + losses), vs the games before.")
        st.metric("Average ELO", "—" if pd.isna(recent["avg_rating"]) else f"{recent['avg_rating']:,.0f}",
                  delta("avg_rating"), border=True)
        st.metric("Average opponent ELO", "—" if pd.isna(recent["avg_opponent_rating"]) else f"{recent['avg_opponent_rating']:,.0f}",
                  delta("avg_opponent_rating"), delta_color="off", border=True)

    if not before["games"]:
        st.info(
            f"No games before {cutoff:%d %b %Y} in the selected dates, so there is nothing to compare with. "
            "Widen the game end date or shorten the recent period.",
            icon=":material/compare_arrows:",
        )

    gap = cube.progression(filters, cutoff, "rating_gap_category", pg_split)
    band = cube.progression(filters, cutoff, "opponent_rating_band", pg_split)
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
