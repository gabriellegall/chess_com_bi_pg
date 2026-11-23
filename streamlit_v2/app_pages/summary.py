"""Summary: the key insights of every page for the recent period, and the lost games worth reviewing.

Recent period: the last session or the last N days (period.py). Usual level: the whole selected period
(game end date), as on the other pages. Results compare with the games before the recent period, as on Results.
"""
import pandas as pd
import streamlit as st

import benchmark
import cube
import period
from benchmark import pct

MIN_GROUP_GAMES = 3  # a kind of opponent or an opening needs this many recent games to be named
MIN_CHANGE = 0.05  # a rate change below 5 points is not called out
NB_REVIEW = 5  # lost games suggested for review

TACTICS = {  # (context, severity): label. Share of games with at least one; lower is better.
    ("throw", "big_blunder"): "Throws · big blunders",
    ("throw", "blunder"): "Throws · blunders",
    ("miss_opp", "big_blunder"): "Missed opportunities · big blunders",
    ("miss_opp", "blunder"): "Missed opportunities · blunders",
}
TECHNIQUE = {  # kpi: label, higher is better, what the rate is computed on
    "conversion": ("Converting a +500 advantage", True, "winning positions"),
    "save": ("Saving a −500 position", True, "lost positions"),
    "early_resignation": ("Resigning above −200", False, "resignations"),
}
CLOCK = {  # kpi: label, higher is better (None: no better side)
    "first_big_blunder": ("Clock left at the first big blunder", None),
    "end_early": ("Clock left after move 15", True),
    "end_mid": ("Clock left after move 35", True),
    "end_late": ("Clock left after move 65", True),
}

filters: cube.Filters = st.session_state.filters
today = st.session_state.today

# ---------- Period ----------
with st.container(border=True):
    st.subheader("Summary")
    st.caption("The key figures of every page for the recent period, against your usual level (the whole selected "
               "game end date) and the other players, then the lost games most worth reviewing.")
    recent_period = period.resolve(period.control("sum_days", default=period.LAST_SESSION), filters, today)

if recent_period.is_session and recent_period.session is None:
    st.stop()  # resolve() already says that no session qualifies
scope = recent_period.scope(filters) or {}  # {}: the recent period covers the whole selected period
has_baseline = bool(scope)
if recent_period.is_session:
    when = f"In your last session ({recent_period.session.start:%a %d %b}, from {recent_period.session.start:%H:%M})"
else:
    when = f"In the {recent_period.label.lower()}"

res = cube.results(filters, **scope)
if not res["games"]:
    st.info(f"No games in the {recent_period.label.lower()} under these filters.", icon=":material/filter_alt_off:")
    st.stop()
games = cube.games_detail(filters, **scope)


# ---------- Helpers ----------
def wins_in(wins: int, games: int) -> str:
    return f"{wins} win{'s' if wins != 1 else ''} in {games} game{'s' if games != 1 else ''}"


def points(change: float) -> str:
    return f"{round(change * 100) + 0:+d} pts"  # + 0: no "-0"


def kpi_cards(items: list[dict]) -> None:
    """One metric per KPI: recent value, change against your usual level, rank among the other players."""
    for col, k in zip(st.columns(len(items)), items):
        with col:
            hib = k["higher_is_better"]
            change = k["recent"] - k["usual"] if has_baseline else float("nan")
            st.metric(
                k["label"], pct(k["recent"]),
                None if pd.isna(change) else f"{points(change)} vs usual {pct(k['usual'])}",
                delta_color="off" if hib is None else ("normal" if hib else "inverse"), border=True,
            )
            note = f"{k['n']:,} {k['counted']}"
            r = benchmark.rank(k["peers"], k["recent"], hib)
            if pd.notna(r):
                note += f" · {'more' if hib is None else 'better'} than {r:.0%} of players"
            st.caption(note)


def headline(items: list[dict]) -> str:
    """The clearest worsening and improvement against your usual level, or a note that nothing moved."""
    if not has_baseline:
        return "The recent period covers the whole selected period: there is no usual level to compare with."
    moves = []
    for k in items:
        change = k["recent"] - k["usual"]
        if k["higher_is_better"] is None or pd.isna(change) or k["n"] < MIN_GROUP_GAMES or abs(change) < MIN_CHANGE:
            continue
        moves.append((change if k["higher_is_better"] else -change, k))
    if not moves:
        return "In line with your usual level."
    out = []
    worst, best = min(moves, key=lambda m: m[0]), max(moves, key=lambda m: m[0])
    if worst[0] < 0:
        k = worst[1]
        out.append(f":red[**Worse:**] {k['label'].lower()}, {pct(k['recent'])} against {pct(k['usual'])} usually.")
    if best[0] > 0:
        k = best[1]
        out.append(f":green[**Better:**] {k['label'].lower()}, {pct(k['recent'])} against {pct(k['usual'])} usually.")
    return "  \n".join(out)


def others_of(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["username_global"] != filters.player]


# ---------- Results ----------
with st.container(border=True):
    st.subheader(":material/trending_up: Results")
    split_point = recent_period.session or recent_period.cutoff
    before = cube.progression_summary(filters, split_point).loc["before"]
    n, w, d, l = (int(res[c]) for c in ("games", "wins", "draws", "losses"))
    lines = [f"{when}, you played **{n} games**: {w} wins, {d} draws and {l} losses, "
             f"a win rate of **{pct(res['win_rate'])}**"]
    if before["games"] and pd.notna(res["win_rate"]) and pd.notna(before["win_rate"]):
        lines[0] += f" ({points(res['win_rate'] - before['win_rate'])} against {pct(before['win_rate'])} before)"
    lines[0] += "."
    for tc, g in games.groupby("time_class"):
        first, last = int(g["playing_rating"].iloc[0]), int(g["playing_rating"].iloc[-1])
        lines.append(f"Your {tc} ELO went from **{first}** (first game) to **{last}** (last game), "
                     f"**{last - first:+d}**." if len(g) > 1 else f"Your {tc} ELO: **{first}** (one game).")
    gap = cube.progression(filters, split_point, "rating_gap_category", False)
    gap = gap[gap["recent_games"] >= MIN_GROUP_GAMES].dropna(subset=["recent_win_rate"])
    if len(gap) >= 2:
        best, worst = gap.loc[gap["recent_win_rate"].idxmax()], gap.loc[gap["recent_win_rate"].idxmin()]
        lines.append(
            f"You did best against **{best['rating_gap_category'].lower()}** opponents "
            f"({wins_in(best['recent_wins'], best['recent_games'])}) and worst against "
            f"**{worst['rating_gap_category'].lower()}** opponents ({wins_in(worst['recent_wins'], worst['recent_games'])})."
        )
    elif len(gap) == 1:
        g = gap.iloc[0]
        lines.append(f"Most of your games were against **{g['rating_gap_category'].lower()}** opponents "
                     f"({wins_in(g['recent_wins'], g['recent_games'])}).")
    st.markdown("  \n".join(lines))
    st.caption("Opponents: much weaker (> 50 below your rating), weaker (16–50 below), similar (within 15), "
               f"stronger, much stronger. A kind of opponent is named with at least {MIN_GROUP_GAMES} games.")

# ---------- Tactics ----------
with st.container(border=True):
    st.subheader(":material/extension: Tactics")
    t_usual, t_peers = cube.blunder_shares(filters), others_of(cube.blunder_shares(
        filters, all_players=True, min_games=benchmark.MIN_GAMES))
    t_recent = cube.blunder_shares(filters, **scope) if scope else t_usual

    def blunder_kpi(df: pd.DataFrame, c: str, s: str) -> pd.DataFrame:
        return df[(df["context"] == c) & (df["severity"] == s) & (df["phase"] == "all")]

    items = []
    for (c, s), label in TACTICS.items():
        rec, usu = blunder_kpi(t_recent, c, s), blunder_kpi(t_usual, c, s)
        items.append({"label": label, "higher_is_better": False, "counted": "games",
                      "recent": rec["share"].iloc[0] if not rec.empty else float("nan"),
                      "usual": usu["share"].iloc[0] if not usu.empty else float("nan"),
                      "n": int(rec["games"].iloc[0]) if not rec.empty else 0,
                      "peers": blunder_kpi(t_peers, c, s)["share"]})
    st.markdown(headline(items))
    st.caption("Share of games with at least one blunder of that kind. Throw: from an even or losing position; "
               "missed opportunity: from a winning one.")
    kpi_cards(items)

# ---------- Technique ----------
with st.container(border=True):
    st.subheader(":material/chess: Technique")
    items = []
    for kpi, (label, hib, counted) in TECHNIQUE.items():
        usu = cube.technique_rate(filters, kpi)
        rec = cube.technique_rate(filters, kpi, **scope) if scope else usu
        peers = others_of(cube.technique_rate(filters, kpi, all_players=True, min_games=benchmark.MIN_GAMES))
        items.append({"label": label, "higher_is_better": hib, "counted": counted,
                      "recent": rec["share"].iloc[0] if not rec.empty else float("nan"),
                      "usual": usu["share"].iloc[0] if not usu.empty else float("nan"),
                      "n": int(rec["games"].iloc[0]) if not rec.empty else 0, "peers": peers["share"]})
    st.markdown(headline(items))
    kpi_cards(items)

# ---------- Clock ----------
with st.container(border=True):
    st.subheader(":material/timer: Clock")
    items = []
    for kpi, (label, hib) in CLOCK.items():
        usu = cube.clock_rate(filters, kpi)
        rec = cube.clock_rate(filters, kpi, **scope) if scope else usu
        peers = others_of(cube.clock_rate(filters, kpi, all_players=True, min_games=benchmark.MIN_GAMES))
        items.append({"label": label, "higher_is_better": hib, "counted": "games",
                      "recent": rec["share"].iloc[0] if not rec.empty else float("nan"),
                      "usual": usu["share"].iloc[0] if not usu.empty else float("nan"),
                      "n": int(rec["games"].iloc[0]) if not rec.empty else 0, "peers": peers["share"]})
    st.markdown(headline(items))
    st.caption("Average share of the starting clock left. At the first big blunder there is no better side: "
               "lots of time left points to tactics, little to time management.")
    kpi_cards(items)

# ---------- Openings ----------
with st.container(border=True):
    st.subheader(":material/menu_book: Openings")
    o_recent = cube.opening_results(filters, **scope)
    o = o_recent.merge(cube.opening_results(filters)[["playing_as", "opening", "win_rate"]]
                       .rename(columns={"win_rate": "usual_win_rate"}), on=["playing_as", "opening"], how="left")
    o = o.sort_values("games", ascending=False)

    def describe(r: pd.Series) -> str:
        text = f"**{r['opening']}** as {r['playing_as']} ({wins_in(r['wins'], r['games'])}"
        if has_baseline and pd.notna(r["usual_win_rate"]):
            text += f", {pct(r['usual_win_rate'])} won usually"
        return text + ")"

    lines = [f"Most played: {describe(o.iloc[0])}."]
    rated = o[o["games"] >= MIN_GROUP_GAMES].dropna(subset=["win_rate"])
    if len(rated) >= 2:
        best, worst = rated.loc[rated["win_rate"].idxmax()], rated.loc[rated["win_rate"].idxmin()]
        lines.append(f":green[**Best:**] {describe(best)}.  \n:red[**Worst:**] {describe(worst)}.")
    st.markdown("  \n".join(lines))
    st.dataframe(
        o.head(8)[["playing_as", "opening", "games", "wins", "draws", "losses", "win_rate", "usual_win_rate"]]
        .assign(win_rate=lambda d: d["win_rate"] * 100, usual_win_rate=lambda d: d["usual_win_rate"] * 100),
        hide_index=True,
        column_config={
            "playing_as": "Colour", "opening": "Opening", "games": "Games", "wins": "Wins", "draws": "Draws",
            "losses": "Losses",
            "win_rate": st.column_config.NumberColumn("Win rate", format="%.0f%%"),
            "usual_win_rate": st.column_config.NumberColumn("Usual win rate", format="%.0f%%"),
        },
    )
    st.caption(f"Win rate: wins ÷ (wins + losses). Best and worst need {MIN_GROUP_GAMES} games.")


# ---------- Games to review ----------
def review_reasons(g: pd.Series) -> list[tuple[int, str, str]]:
    """Why a lost game is worth reviewing: (weight, page, reason)."""
    reasons = []
    if pd.notna(g["max_score_playing"]) and g["max_score_playing"] > 500:
        reasons.append((3, "Technique", f"You were winning, up to {g['max_score_playing']:+.0f}"))
    if g["playing_result_detailed"] == "resigned" and pd.notna(g["final_score_playing"]) and g["final_score_playing"] > -200:
        reasons.append((3, "Technique", f"Resigned at {g['final_score_playing']:+.0f}, still playable"))
    if g["playing_result_detailed"] == "timeout":
        better = pd.notna(g["final_score_playing"]) and g["final_score_playing"] > 0
        reasons.append((3 if better else 2, "Clock", "Lost on time" + (" in a better position" if better else "")))
    if pd.notna(g["first_miss_opp_big_blunder_playing_prct_time_remaining"]):
        reasons.append((2, "Tactics", "Big blunder from a winning position, with "
                        f"{g['first_miss_opp_big_blunder_playing_prct_time_remaining']:.0%} of the clock left"))
    if pd.notna(g["first_throw_big_blunder_playing_prct_time_remaining"]):
        reasons.append((2, "Tactics", "Big blunder from an even position, with "
                        f"{g['first_throw_big_blunder_playing_prct_time_remaining']:.0%} of the clock left"))
    if g["rating_gap_category"] in ("Weaker", "Much weaker"):
        reasons.append((1, "Results", f"Lost to a {g['rating_gap_category'].lower()} opponent"))
    return reasons


BADGE = {"Technique": "violet", "Clock": "orange", "Tactics": "red", "Results": "blue"}

with st.container(border=True):
    st.subheader(":material/rate_review: Lost games to review")
    lost = games[games["playing_result"] == "Lose"].copy()
    lost["reasons"] = lost.apply(review_reasons, axis=1)
    lost["weight"] = lost["reasons"].map(lambda rs: sum(r[0] for r in rs))
    picks = (lost[lost["weight"] > 0]
             .sort_values(["weight", "end_time"], ascending=[False, False])
             .head(NB_REVIEW))
    st.caption(f"{len(lost)} lost games in the {recent_period.label.lower()}. The most instructive first (then the most recent): a win "
               "let slip, a resignation or a loss on time in a playable position, then big blunders, then losses to "
               "weaker opponents.")
    if picks.empty:
        st.info("None of your losses in this period has a clear lesson: no winning position let slip, "
                "no big blunder, no early resignation or loss on time.", icon=":material/thumb_up:")
    for _, g in picks.iterrows():
        with st.container(border=True, horizontal=True, vertical_alignment="center", gap="medium"):
            with st.container():
                st.markdown(
                    f"**{g['end_time']:%a %d %b %H:%M}** · {g['time_class']} · {g['playing_as']} · "
                    f"{g['playing_rating']:.0f} vs {g['opponent_rating']:.0f} · "
                    f"{g['opening_level_7_name'] or 'Unknown opening'} · {g['nb_moves'] or 0:.0f} moves · "
                    f"{g['playing_result_detailed']}"
                )
                st.markdown("  ".join(f":{BADGE[page]}-badge[{page}] {reason}" for _, page, reason in g["reasons"]))
            if g["url"]:
                st.link_button("Review", g["url"], icon=":material/open_in_new:", width="content")
