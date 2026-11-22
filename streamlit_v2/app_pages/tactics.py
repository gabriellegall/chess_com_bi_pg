"""Tactics: how often I blunder, by kind (throw vs missed opportunity), severity and game phase, against similar players.

Reads the global filters set by app.py from st.session_state.
"""
from datetime import timedelta

import pandas as pd
import streamlit as st

import benchmark
import charts
import cube

MIN_PEER_GAMES = 10
RESULTS = {"All games": None, "Won": "Win", "Lost": "Lose"}
PHASES = {"all": "All phases", "early": "Early · moves 1–15", "mid": "Mid · moves 16–35", "late": "Late · moves 36–65"}
SEVERITIES = {
    "blunder": ("Blunders", "A move that drops the engine evaluation by 250 to 600 centipawns, from a position "
                            "that was not already lost (above −200) to one that is no longer winning (below +200)."),
    "big_blunder": ("Big blunders", "Same as a blunder, with a drop of more than 600 centipawns. "
                                    "Each move counts in one severity only."),
}
CONTEXTS = {
    "throw": (
        "Throws", ":material/crisis_alert:",
        "A blunder played from an even or losing position (evaluation at most +150 before the move).",
        "Lever: defensive vigilance. Before each move, check what your opponent threatens.",
    ),
    "miss_opp": (
        "Missed opportunities", ":material/visibility_off:",
        "A blunder played from a winning position (evaluation above +150 before the move).",
        "Lever: conversion. When you are winning, stay focused and prefer the safe, simple move.",
    ),
}

filters: cube.Filters = st.session_state.filters
today = st.session_state.today
text_colour = "#fafafa" if st.context.theme.type == "dark" else "#31333f"


# ---------- Controls and data ----------
with st.container(border=True):
    st.subheader("Blunders against similar players")
    st.caption(
        "Lever: puzzles, aimed at the kind of blunder and the game phase where you stand out. "
        f"Each figure is the share of games with at least one blunder of that kind, compared with every other player "
        f"with at least {MIN_PEER_GAMES} games under the same filters (time class, both ELO ranges, game end dates, result)."
    )
    with st.container(horizontal=True, gap="large"):
        result_label = st.segmented_control(
            "Games", list(RESULTS), default="All games", key="tac_result",
            help="Keep only the games you won or lost. The other players are filtered the same way.",
        ) or "All games"
        days = st.segmented_control(
            "Recent period", [30, 60, 90, 180], default=90, format_func=lambda d: f"Last {d} days", key="tac_days",
        ) or 90
    result = RESULTS[result_label]

    recent_start = max(filters.start, today - timedelta(days=days))
    has_recent = recent_start > filters.start
    whole = cube.blunder_shares(filters, result=result)
    recent = cube.blunder_shares(filters, start=recent_start, result=result) if has_recent else whole.iloc[0:0]
    peers = cube.blunder_shares(filters, all_players=True, min_games=MIN_PEER_GAMES, result=result)
    peers = peers[peers["username_global"] != filters.player]

    if whole.empty:
        st.info("No games match these filters.", icon=":material/filter_alt_off:")
        st.stop()

    nb_games, nb_recent = int(whole["games"].iloc[0]), int(recent["games"].iloc[0]) if not recent.empty else 0
    nb_peers = peers["username_global"].nunique()
    st.markdown(
        f":gray[**●** {nb_peers} other players (box: middle half, line: median)]  ·  "
        f":blue[**┃** you, whole period ({nb_games:,} games)]  ·  "
        f"arrow to you, last {days} days ({nb_recent:,} games): :green[**●◀** fewer blunders], :red[more blunders **▶●**]"
    )
    if st.session_state.several_time_classes:
        st.warning("Several time classes are selected: faster games bring more blunders, so players who play "
                   "more bullet or blitz look worse. Pick one time class for a fair comparison.", icon=":material/info:")
    if not nb_peers:
        st.info(f"No other player has {MIN_PEER_GAMES} games or more under these filters. "
                "Widen the ELO ranges or the game end date to get a comparison.", icon=":material/group_off:")
    if nb_games < MIN_PEER_GAMES:
        st.warning(f"Only {nb_games} games for you under these filters: your shares are not reliable yet.",
                   icon=":material/warning:")
    if not has_recent:
        st.caption(f"The last {days} days cover the whole selected period, so there is no recent trend to show. "
                   "Widen the game end date or shorten the recent period.")


def summary(context: str, severity: str, phases: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The other players' rows, and yours (whole period, recent days, rank among the others, label), for one kind."""
    def pick(df: pd.DataFrame) -> pd.DataFrame:
        return df[(df["context"] == context) & (df["severity"] == severity) & df["phase"].isin(phases)]

    others = pick(peers).assign(row=lambda d: d["phase"].map(PHASES))
    you = benchmark.compare(others, pick(whole), pick(recent), "phase", higher_is_better=False, unit="of games",
                            days=days, has_recent=has_recent)
    you["row"] = you["phase"].map(PHASES)
    return others, you


def render(context: str, severity: str, phases: list[str]) -> None:
    """One chart per phase, each with its own x scale so that rare blunders (early, big) stay readable."""
    title, help_text = SEVERITIES[severity]
    st.markdown(f"**{title}**", help=help_text)
    others, you = summary(context, severity, phases)
    for i, phase in enumerate(phases):
        st.altair_chart(charts.peer_distribution(
            others[others["phase"] == phase], you[you["phase"] == phase], text_colour,
            axis_title="Share of games with at least one" if i == len(phases) - 1 else None,
        ))


# ---------- Throws, then missed opportunities ----------
for context, (title, icon, definition, lever) in CONTEXTS.items():
    with st.container(border=True):
        st.subheader(f"{icon} {title}")
        st.caption(f"{definition} {lever}")
        for col, severity in zip(st.columns(2, gap="large"), SEVERITIES):
            with col:
                render(context, severity, ["all"])
        with st.expander("Breakdown by game phase", icon=":material/timeline:"):
            st.caption("Share of games with at least one blunder of that kind in each phase. Each phase has its own "
                       "scale: compare your position among the players, not the lengths between phases. "
                       "Moves after 65 belong to no phase: they only count in the overall figure above.")
            for col, severity in zip(st.columns(2, gap="large"), SEVERITIES):
                with col:
                    render(context, severity, ["early", "mid", "late"])
