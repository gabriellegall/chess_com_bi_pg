"""Chess improvement (v2): entry point with the shared filters header and the page navigation.

Run from the repository root: streamlit run streamlit_v2/app.py
Data: Cube SQL API (views v_games); every filter is applied by Cube.
The filters are passed to the pages (app_pages/) through st.session_state.
"""
from datetime import date

import pandas as pd
import streamlit as st

import charts
import cube

st.set_page_config(page_title="Chess improvement", page_icon=":material/chess:", layout="wide")

page = st.navigation(
    [
        st.Page("app_pages/results.py", title="Results & context", icon=":material/trending_up:", default=True),
        st.Page("app_pages/tactics.py", title="Tactics", icon=":material/extension:", url_path="tactics"),
        st.Page("app_pages/technique.py", title="Technique", icon=":material/chess:", url_path="technique"),
        st.Page("app_pages/clock.py", title="Clock", icon=":material/timer:", url_path="clock"),
        st.Page("app_pages/openings.py", title="Openings", icon=":material/menu_book:", url_path="openings"),
    ],
    position="top",
)

st.title("What should I work on to win more?")
st.caption(f"{page.title} · every figure is a Cube measure of the view `v_games`, filtered by Cube.")

# ---------- Filters header ----------
players = cube.players()
if players.empty:
    st.error("Cube returned no players. Check that Cube is running and the SQL API credentials in `.env` are set.")
    st.stop()

today = date.today()
PERIODS = {"Last month": 1, "Last 3 months": 3, "Last 6 months": 6, "Last 12 months": 12, "All games": None, "Custom range": "custom"}


def band_bounds(rows: pd.DataFrame, col: str) -> tuple[int, int]:
    """Slider bounds covering the 50-point rating bands present in `rows`."""
    lo, hi = int(rows[col].min()), int(rows[col].max()) + 50
    return lo, max(hi, lo + 50)


def overlapping(bands: pd.Series, selection: tuple[int, int] | None) -> pd.Series:
    """Bands [b, b + 50) that meet the selected rating range (every band when nothing is selected yet)."""
    if selection is None:
        return pd.Series(True, index=bands.index)
    return (bands <= selection[1]) & (bands + 50 > selection[0])


def narrowed(key: str) -> tuple[int, int] | None:
    """A range slider's selection, or None while it is left on its full range (it then constrains nothing)."""
    value, previous = st.session_state.get(key), st.session_state.get(f"_{key}_bounds")
    return None if value is None or previous is None or tuple(value) == tuple(previous) else tuple(value)


def sync_slider(key: str, bounds: tuple[int, int]) -> None:
    """Set a range slider's value before it is drawn, for its new bounds.

    A slider left on its full range follows its bounds; a narrowed one is kept, clamped to the bounds
    (and reset to the full range when nothing of it is left).
    """
    value = narrowed(key)
    if value is None:
        value = bounds
    else:
        value = (max(value[0], bounds[0]), min(value[1], bounds[1]))
        if value[0] >= value[1]:
            value = bounds
    st.session_state[key] = value
    st.session_state[f"_{key}_bounds"] = bounds


g_you, g_all = st.columns([2, 3], gap="small")
with g_you.container(border=True, height="stretch"):
    st.markdown(":material/person: **You only**")
    c_player, c_date = st.columns(2, gap="medium")
with g_all.container(border=True, height="stretch"):
    st.markdown(":material/groups: **You and the players you are compared with**")
    c_tc, c_elo, c_opp = st.columns([1.1, 1, 1], gap="medium")


# Player, time class and game end date are independent of each other.
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

# A new player starts again from the full ELO ranges.
if st.session_state.get("_elo_player") != player:
    for key in ("elo", "opp_elo"):
        st.session_state.pop(key, None)
        st.session_state.pop(f"_{key}_bounds", None)
    st.session_state["_elo_player"] = player

with c_tc:
    tc_options = [t for t in charts.TIME_CLASS_COLOURS if t in set(profile["time_class"])]
    time_classes = st.pills(
        "Time class", tc_options, selection_mode="multi", format_func=str.capitalize,
        default=["rapid"] if "rapid" in tc_options else tc_options[:1],
        key=f"tc_{player}", help="Leave empty to include every time class.",
    )

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

# The ELO sliders only offer the ratings met with the player, time classes and dates above,
# and each one only those met within the other's selection when that one is narrowed.
scope = profile[(profile["day"] >= start) & (profile["day"] <= end)]
if time_classes:
    scope = scope[scope["time_class"].isin(time_classes)]
if scope.empty:
    scope = profile  # no games: keep usable sliders, the pages say there is nothing to show
elo_rows = scope[overlapping(scope["opponent_rating_band"], narrowed("opp_elo"))]
opp_rows = scope[overlapping(scope["playing_rating_band"], narrowed("elo"))]
elo_bounds = band_bounds(elo_rows if not elo_rows.empty else scope, "playing_rating_band")
opp_bounds = band_bounds(opp_rows if not opp_rows.empty else scope, "opponent_rating_band")
sync_slider("elo", elo_bounds)
sync_slider("opp_elo", opp_bounds)

with c_elo:
    elo = st.slider("Player ELO", *elo_bounds, step=25, key="elo")

with c_opp:
    opp_elo = st.slider("Opponent ELO", *opp_bounds, step=25, key="opp_elo")

filters = cube.Filters(
    player=player,
    time_classes=tuple(time_classes or ()),
    elo=(int(elo[0]), int(elo[1])),
    opp_elo=(int(opp_elo[0]), int(opp_elo[1])),
    start=start,
    end=end,
)
st.session_state.filters = filters
st.session_state.today = today
st.session_state.several_time_classes = len(time_classes or tc_options) > 1

page.run()
