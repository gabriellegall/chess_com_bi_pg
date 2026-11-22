"""Technique: converting winning positions, saving lost ones, not resigning too early, against similar players.

Reads the global filters set by app.py from st.session_state.
"""
from datetime import timedelta

import streamlit as st

import benchmark
import charts
import cube

MIN_PEER_GAMES = 10
# kpi: title, icon, definition, lever, higher is better, label unit, axis title
KPIS = {
    "conversion": (
        "Converting a decisive advantage", ":material/trophy:",
        "Games where your evaluation went above +500 at some point, and the share of them you won.",
        "Lever: endgames and winning technique. Trade down, remove counterplay, keep it simple.",
        True, "won", "Share of games won after reaching +500",
    ),
    "save": (
        "Saving lost positions", ":material/shield:",
        "Games where your evaluation fell below −500 at some point, and the share of them you still won or drew.",
        "Lever: defence. Look for resources, set traps and make the win hard to find.",
        True, "saved", "Share of games won or drawn after falling below −500",
    ),
    "early_resignation": (
        "Resigning too early", ":material/flag:",
        "Your resignations where the last evaluation was still above −200, i.e. the position was playable.",
        "Lever: don't resign too early. Play on while the position is still holding.",
        False, "of resignations", "Share of resignations with an evaluation above −200",
    ),
}

filters: cube.Filters = st.session_state.filters
today = st.session_state.today
text_colour = "#fafafa" if st.context.theme.type == "dark" else "#31333f"

# ---------- Controls ----------
with st.container(border=True):
    st.subheader("Technique against similar players")
    st.caption(
        "What happens once the game is decided on the board. Each rate is compared with every other player with "
        f"at least {MIN_PEER_GAMES} games counted for that rate under the same filters (time class, both ELO ranges, "
        "game end dates). Evaluations are in centipawns, from your side."
    )
    days = st.segmented_control(
        "Recent period", [30, 60, 90, 180], default=90, format_func=lambda d: f"Last {d} days", key="tech_days",
    ) or 90
    recent_start = max(filters.start, today - timedelta(days=days))
    has_recent = recent_start > filters.start
    st.markdown(
        ":gray[**●** other players (box: middle half, line: median)]  ·  :blue[**┃** you, whole period]  ·  "
        f"arrow to you, last {days} days: :green[**green** when better], :red[**red** when worse]"
    )
    if st.session_state.several_time_classes:
        st.warning(cube.TC_HINT, icon=":material/info:")
    if not has_recent:
        st.caption(f"The last {days} days cover the whole selected period, so there is no recent trend to show. "
                   "Widen the game end date or shorten the recent period.")

# ---------- One section per KPI ----------
for kpi, (title, icon, definition, lever, higher_is_better, unit, axis_title) in KPIS.items():
    with st.container(border=True):
        st.subheader(f"{icon} {title}")
        st.caption(f"{definition} {lever}")
        whole = cube.technique_rate(filters, kpi)
        recent = cube.technique_rate(filters, kpi, start=recent_start) if has_recent else whole.iloc[0:0]
        others = cube.technique_rate(filters, kpi, all_players=True, min_games=MIN_PEER_GAMES)
        others = others[others["username_global"] != filters.player]

        nb_games = int(whole["games"].iloc[0]) if not whole.empty else 0
        if not nb_games:
            st.info("None of your games under these filters counts for this rate.", icon=":material/filter_alt_off:")
            continue
        you = benchmark.compare(others, whole, recent, "kpi", higher_is_better=higher_is_better, unit=unit,
                                days=days, has_recent=has_recent)
        you["row"] = f"You: {nb_games:,} games"
        others = others.assign(row=you["row"].iloc[0])

        st.altair_chart(charts.peer_distribution(others, you, text_colour, axis_title=axis_title))
        notes = []
        if others.empty:
            notes.append(f"No other player has {MIN_PEER_GAMES} such games under these filters: widen them to compare.")
        else:
            notes.append(f"{len(others)} other players.")
        if nb_games < MIN_PEER_GAMES:
            notes.append(f"Only {nb_games} such games for you: the rate is not reliable yet.")
        if has_recent:
            notes.append(f"{int(you['recent_games'].iloc[0]):,} such games in the last {days} days.")
        st.caption(" ".join(notes))
