"""Openings: win rate per opening (whole period and recent period), evaluation over the moves, raw games.

Replicates the openings section of the v1 app (streamlit/), on the global filters set by app.py.
"""
import streamlit as st

import charts
import cube
import period

MIN_OPENING_GAMES = 10  # openings shown in the evaluation charts
LEVEL_TITLES = ["Family", "Opening", "Variation", "First 7 moves"]

filters: cube.Filters = st.session_state.filters
today = st.session_state.today

# ---------- Controls ----------
with st.container(border=True):
    st.subheader("How do you do on your openings?")
    st.caption(
        "Your games by opening, from the family in the centre to the exact first 7 moves outside. "
        "Size: games played. Colour: win rate, wins ÷ (wins + losses), red below 50% and green above."
    )
    with st.container(horizontal=True, gap="large"):
        playing_as = st.segmented_control("Playing as", ["White", "Black"], default="White", key="open_colour") or "White"
        recent_period = period.resolve(period.control("open_days"), filters, today)
    recent_scope = recent_period.scope(filters)

tree = cube.opening_tree(filters, playing_as)
if tree.empty:
    st.info(f"No games as {playing_as} under these filters.", icon=":material/filter_alt_off:")
    st.stop()

# ---------- Win rate per opening ----------
with st.container(border=True):
    st.subheader(":material/donut_large: Win rate per opening")
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(f"**All games** · {int(tree['games'].sum()):,} games")
        st.plotly_chart(charts.opening_sunburst(tree, cube.OPENING_LEVELS), key="sunburst_all")
    with right:
        recent = cube.opening_tree(filters, playing_as, **recent_scope) if recent_scope else tree.iloc[0:0]
        st.markdown(f"**{recent_period.label}** · {int(recent['games'].sum()):,} games")
        if recent.empty:
            st.info(f"No games as {playing_as} in the {recent_period.label.lower()}.", icon=":material/history:")
        else:
            st.plotly_chart(charts.opening_sunburst(recent, cube.OPENING_LEVELS), key="sunburst_recent")
    st.caption("Click a ring to zoom into it, click the centre to zoom back out.")

# ---------- Evaluation over the moves ----------
games = cube.opening_games(filters, playing_as)
with st.container(border=True):
    st.subheader(":material/show_chart: Evaluation over the moves, by opening")
    st.caption(
        f"Your evaluation every 5 moves, in centipawns (capped at ±1000), for each variation with at least "
        f"{MIN_OPENING_GAMES} games. Box: middle half of the games, whiskers: the usual range, diamond: the median. "
        "Colour: red when you are worse on median, green when you are better, grey when balanced."
    )
    counts = games["opening_level_7_name"].value_counts()
    openings = counts[counts >= MIN_OPENING_GAMES].index.tolist()
    if not openings:
        st.info(f"No variation with {MIN_OPENING_GAMES} games as {playing_as} under these filters.",
                icon=":material/filter_alt_off:")
    cols = st.columns(2, gap="large")
    for i, opening in enumerate(openings):
        with cols[i % 2]:
            st.altair_chart(charts.score_by_move(games[games["opening_level_7_name"] == opening], cube.SCORE_TURNS,
                                                 f"{opening} ({counts[opening]} games)"))

# ---------- Raw data ----------
with st.container(border=True):
    st.subheader(":material/table: Your games")
    raw = games
    pick_cols = st.columns(len(cube.OPENING_LEVELS))
    for col, level, title in zip(pick_cols, cube.OPENING_LEVELS, LEVEL_TITLES):
        with col:
            choice = st.selectbox(title, ["All", *sorted(raw[level].unique())], key=f"open_raw_{level}")
        if choice != "All":
            raw = raw[raw[level] == choice]
    st.dataframe(
        raw,
        hide_index=True,
        column_config={
            "end_time": st.column_config.DatetimeColumn("End time", format="DD MMM YYYY HH:mm"),
            "url": st.column_config.LinkColumn("Game", display_text="Open"),
            "eco": st.column_config.LinkColumn("Opening page", display_text="chess.com"),
            "time_class": "Time class", "playing_as": "Colour", "playing_result": "Result",
            "playing_rating": "Your ELO", "opponent_rating": "Opponent ELO",
            **{lvl: st.column_config.TextColumn(t) for lvl, t in zip(cube.OPENING_LEVELS, LEVEL_TITLES)},
            **{f"score_playing_turn_{t}": st.column_config.NumberColumn(f"Eval. move {t}", format="%+d")
               for t in cube.SCORE_TURNS},
        },
    )
    st.caption(f"{len(raw):,} games.")
