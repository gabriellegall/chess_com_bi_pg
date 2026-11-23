"""Clock: time left at the first big blunder and at the end of each game phase.

Against similar players, with the recent period as on the other pages. Reads the global filters set by app.py.
"""
import streamlit as st

import benchmark
import charts
import cube
import period

MIN_PEER_GAMES = benchmark.MIN_GAMES
# kpi: row label, higher is better (None: no better side), label unit
KPIS = {
    "first_big_blunder": ("At the first big blunder", None, "of the clock left"),
    "end_early": ("Early · after move 15", True, "of the clock left"),
    "end_mid": ("Mid · after move 35", True, "of the clock left"),
    "end_late": ("Late · after move 65", True, "of the clock left"),
}

filters: cube.Filters = st.session_state.filters
today = st.session_state.today
text_colour = "#fafafa" if st.context.theme.type == "dark" else "#31333f"

# ---------- Controls ----------
with st.container(border=True):
    st.subheader("Clock against similar players")
    st.caption(
        "How you use your time, as a share of your starting clock (increments can take it above 100%). "
        f"Each figure is compared with {benchmark.SCOPE}. Time left is the average over the games."
    )
    recent_period = period.resolve(period.control("clock_days"), filters, today)
    recent_scope = recent_period.scope(filters)
    has_recent = recent_scope is not None
    st.markdown(
        ":gray[**●** other players (box: middle half, line: median)]  ·  :blue[**┃** you, whole period]  ·  "
        f"arrow to you, {recent_period.label.lower()}: :green[**green** when better], :red[**red** when worse], "
        ":violet[**violet** when there is no better side]"
    )
    if st.session_state.several_time_classes:
        st.warning("Several time classes are selected: clocks are used very differently in bullet, blitz and rapid. "
                   "Pick one time class for a fair comparison.", icon=":material/info:")
    if not has_recent and not recent_period.is_session:
        st.caption(f"The {recent_period.label.lower()} cover the whole selected period, so there is no recent trend "
                   "to show. Widen the game end date or shorten the recent period.")


def render(kpi: str, axis_title: str | None) -> str:
    """Draw one KPI on one row and return a short note on what it is based on."""
    row, higher_is_better, unit = KPIS[kpi]
    whole = cube.clock_rate(filters, kpi)
    recent = cube.clock_rate(filters, kpi, **recent_scope) if has_recent else whole.iloc[0:0]
    others = cube.clock_rate(filters, kpi, all_players=True, min_games=MIN_PEER_GAMES)
    others = others[others["username_global"] != filters.player]
    nb = int(whole["games"].iloc[0]) if not whole.empty else 0
    if not nb or whole["share"].isna().all():
        st.caption(f"**{row}**: none of your games under these filters counts here.")
        return f"{row}: no data for your games."
    you = benchmark.compare(others, whole, recent, "kpi", higher_is_better=higher_is_better, unit=unit,
                            period=recent_period.label, has_recent=has_recent)
    you["row"] = row
    st.altair_chart(charts.peer_distribution(others.assign(row=row), you, text_colour, axis_title=axis_title))
    note = f"Based on your {nb:,} games"
    if has_recent:
        note += f" ({int(you['recent_games'].iloc[0]):,} in the {recent_period.label.lower()})"
    note += f" and {len(others)} other players" if not others.empty else ", no other player to compare with"
    if nb < MIN_PEER_GAMES:
        note += " — too few to be reliable"
    return note + "."


# ---------- Time left at the first big blunder ----------
with st.container(border=True):
    st.subheader(":material/timer: Time left at the first big blunder")
    st.caption("Average share of the clock left when you made the first big blunder of the game (drop of more than "
               "600 centipawns). Lots of time left: a tactics problem, work on puzzles. Little time left: a time "
               "management problem, work on the clock. Neither side is better, so the arrow is violet.")
    st.caption(render("first_big_blunder", "Share of the clock left"))

# ---------- Time left through the game ----------
with st.container(border=True):
    st.subheader(":material/hourglass_bottom: Time left at the end of each phase")
    st.caption(
        "Average share of the clock left after your move at the end of each phase. Each phase has its own scale. "
        "Lever: much time spent in the opening means preparation; regular time trouble later means pace."
    )
    phases = ["end_early", "end_mid", "end_late"]
    notes = [render(kpi, "Share of the clock left" if i == len(phases) - 1 else None) for i, kpi in enumerate(phases)]
    st.caption(" ".join(dict.fromkeys(notes)))  # the same games for every phase: show each note once
