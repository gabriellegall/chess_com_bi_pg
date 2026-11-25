"""Cube SQL API access for the v2 app.

Every number shown in the app is a MEASURE() of the Cube view v_games, and every
filter is pushed to Cube as a WHERE (or HAVING) clause: pandas only merges and reshapes.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import psycopg
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import URL, bindparam, create_engine, text
from sqlalchemy.engine import Engine

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

RESULT_MEASURES = (
    "MEASURE(nb_games_played) AS games, MEASURE(nb_wins) AS wins, MEASURE(nb_draws) AS draws, "
    "MEASURE(nb_losses) AS losses, MEASURE(win_rate) AS win_rate"
)
PROGRESSION_DIMENSIONS = {"rating_gap_category", "opponent_rating_band"}
GAP_ORDER = ["Much stronger", "Stronger", "Similar", "Weaker", "Much weaker"]
TC_HINT = "Several time classes are selected and their rating scales differ a lot. Pick one time class for a clean reading."

# Share of games with at least one blunder, by (context, severity, phase): measures prct_games_* of cube_games_stats.
# A "blunder" here excludes big blunders: each move counts in one severity only. "any_blunder" is either severity.
BLUNDER_CONTEXTS = ("throw", "miss_opp")
BLUNDER_SEVERITIES = ("any_blunder", "blunder", "big_blunder")
GAME_PHASES = ("all", "early", "mid", "late")
BLUNDER_MEASURES = {
    (c, s, p): f"prct_games_{c}_{s}_playing" + ("" if p == "all" else f"_{p}")
    for c in BLUNDER_CONTEXTS for s in BLUNDER_SEVERITIES for p in GAME_PHASES
}


@st.cache_resource
def get_engine() -> Engine:
    url = URL.create(
        "postgresql+psycopg",
        username=os.getenv("CUBE_SQL_USER"),
        password=os.getenv("CUBE_SQL_PASSWORD"),
        host=os.getenv("CUBE_SQL_HOST", "localhost"),
        port=int(os.getenv("CUBE_SQL_PORT", "15432")),
        database="db",  # not used by Cube
    )
    # Client-side parameter binding (values are still escaped by psycopg):
    # Cube's SQL API rejects server-bound integer parameters.
    return create_engine(url, connect_args={"cursor_factory": psycopg.ClientCursor}, pool_pre_ping=True)


def run(sql: str, params: dict | None = None) -> pd.DataFrame:
    params = params or {}
    stmt = text(sql)
    lists = [k for k, v in params.items() if isinstance(v, (list, tuple))]
    if lists:
        stmt = stmt.bindparams(*[bindparam(k, expanding=True) for k in lists])
    with get_engine().connect() as conn:
        return pd.read_sql(stmt, conn, params=params)


@dataclass(frozen=True)
class Filters:
    """Global filters of the page, turned into a Cube WHERE clause."""

    player: str
    time_classes: tuple[str, ...]  # empty = every time class
    elo: tuple[int, int]
    opp_elo: tuple[int, int]
    start: date
    end: date  # inclusive

    def where(self, start: date | None = None, end: date | None = None, all_players: bool = False,
              session: str | None = None, until: datetime | None = None) -> tuple[str, dict]:
        """The selected player's games under every filter.

        all_players returns the benchmark instead: every player's games under the time class and both ELO ranges
        (the player, date, session and until filters apply to the selected player alone).
        session keeps only the games of that session (sessions_sk); until keeps only the games ended before it.
        """
        clauses = [
            "playing_rating BETWEEN :elo_lo AND :elo_hi",
            "opponent_rating BETWEEN :opp_lo AND :opp_hi",
        ]
        params = {"elo_lo": self.elo[0], "elo_hi": self.elo[1], "opp_lo": self.opp_elo[0], "opp_hi": self.opp_elo[1]}
        if all_players:
            session = until = None
        else:
            start = self.start if start is None else start
            end = self.end if end is None else end
            clauses = ["username_global = :player", *clauses, "end_time >= :start", "end_time < :end_excl"]
            params |= {
                "player": self.player,
                "start": start.isoformat(), "end_excl": (end + timedelta(days=1)).isoformat(),
            }
        if self.time_classes:
            clauses.append("time_class IN :time_classes")
            params["time_classes"] = list(self.time_classes)
        if session is not None:
            clauses.append("sessions_sk = :session")
            params["session"] = session
        if until is not None:
            clauses.append("end_time < :until")
            params["until"] = until.isoformat()
        return "WHERE " + " AND ".join(clauses), params


@dataclass(frozen=True)
class Session:
    """A session of the selected player: see int_games_sessions in dbt."""

    sessions_sk: str
    start: datetime  # end time of its first game
    games: int  # games of the session under the filters


@st.cache_data(ttl="10m")
def last_session(f: Filters, min_games: int) -> Session | None:
    """The most recent session with at least min_games games under the filters, or None."""
    where, params = f.where()
    params["min_games"] = min_games
    df = run(
        f"SELECT sessions_sk, session_start_time, MEASURE(nb_games_played) AS games FROM v_games {where} "
        "GROUP BY 1, 2 HAVING MEASURE(nb_games_played) >= :min_games ORDER BY 2 DESC LIMIT 1",
        params,
    )
    if df.empty:
        return None
    row = df.iloc[0]
    return Session(row["sessions_sk"], pd.Timestamp(row["session_start_time"]).to_pydatetime(), int(row["games"]))


@st.cache_data(ttl="10m")
def players() -> pd.DataFrame:
    return run("SELECT username_global, MEASURE(nb_games_played) AS games FROM v_games GROUP BY 1 ORDER BY 2 DESC")


@st.cache_data(ttl="10m")
def player_profile(player: str) -> pd.DataFrame:
    """Time classes, rating bands and days played: bounds for the filter widgets."""
    return run(
        "SELECT time_class, playing_rating_band, opponent_rating_band, DATE_TRUNC('day', end_time) AS day, "
        "MEASURE(nb_games_played) AS games FROM v_games WHERE username_global = :player GROUP BY 1, 2, 3, 4",
        {"player": player},
    )


@st.cache_data(ttl="10m")
def elo_trend(f: Filters) -> pd.DataFrame:
    """One row per game: its time class, end time, the player's rating after it, the opponent's rating and the result."""
    where, params = f.where()
    return run(
        "SELECT time_class, end_time, games_sk, playing_rating, opponent_rating, playing_result, "
        f"MEASURE(nb_games_played) AS games FROM v_games {where} GROUP BY 1, 2, 3, 4, 5, 6 ORDER BY 2",
        params,
    )


@st.cache_data(ttl="10m")
def elo_matrix(f: Filters, split: bool) -> pd.DataFrame:
    where, params = f.where()
    dims = (["playing_as"] if split else []) + ["playing_rating_band", "opponent_rating_band"]
    df = run(
        f"SELECT {', '.join(dims)}, {RESULT_MEASURES} FROM v_games {where} "
        f"GROUP BY {', '.join(str(i + 1) for i in range(len(dims)))}",
        params,
    )
    if not split:
        df.insert(0, "playing_as", "All games")
    return df


def _periods(f: Filters, recent: date | Session) -> dict[str, dict | None]:
    """The f.where() arguments of each period, None when the period is empty.

    recent is a cutoff day: before = from the filter start to the day before it, recent = from it to the filter end.
    recent is a session: before = the games ended before the session started, recent = the games of the session.
    """
    if isinstance(recent, Session):
        return {"before": {"until": recent.start}, "recent": {"session": recent.sessions_sk}}
    before_end, recent_start = min(f.end, recent - timedelta(days=1)), max(f.start, recent)
    return {
        "before": {"end": before_end} if f.start <= before_end else None,
        "recent": {"start": recent_start} if recent_start <= f.end else None,
    }


@st.cache_data(ttl="10m")
def progression_summary(f: Filters, recent: date | Session) -> pd.DataFrame:
    rows = []
    for period, scope in _periods(f, recent).items():
        row = {"period": period, "games": 0, "win_rate": None, "avg_rating": None, "avg_opponent_rating": None}
        if scope is not None:
            where, params = f.where(**scope)
            df = run(
                "SELECT MEASURE(nb_games_played) AS games, MEASURE(win_rate) AS win_rate, "
                "MEASURE(avg_playing_rating) AS avg_rating, MEASURE(avg_opponent_rating) AS avg_opponent_rating "
                f"FROM v_games {where}",
                params,
            )
            if not df.empty:
                row.update(df.iloc[0].to_dict())
        rows.append(row)
    return pd.DataFrame(rows).set_index("period")


@st.cache_data(ttl="10m")
def progression(f: Filters, recent: date | Session, dimension: str, split: bool) -> pd.DataFrame:
    """Results before vs recent, one row per dimension value (and colour when split), with the win rate change."""
    if dimension not in PROGRESSION_DIMENSIONS:
        raise ValueError(dimension)
    dims = (["playing_as"] if split else []) + [dimension]
    frames = []
    for period, scope in _periods(f, recent).items():
        if scope is None:
            continue
        where, params = f.where(**scope)
        df = run(
            f"SELECT {', '.join(dims)}, {RESULT_MEASURES} FROM v_games {where} "
            f"GROUP BY {', '.join(str(i + 1) for i in range(len(dims)))}",
            params,
        )
        frames.append(df.set_index(dims).add_prefix(f"{period}_"))
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, axis=1).reset_index()
    for period in ("before", "recent"):
        for col in ("games", "wins", "draws", "losses"):
            name = f"{period}_{col}"
            out[name] = out[name].fillna(0).astype(int) if name in out else 0
        rate = f"{period}_win_rate"
        out[rate] = pd.to_numeric(out[rate], errors="coerce") if rate in out else float("nan")
    out["change"] = out["recent_win_rate"] - out["before_win_rate"]
    if not split:
        out.insert(0, "playing_as", "All games")
    return out


@st.cache_data(ttl="10m")
def blunder_shares(f: Filters, start: date | None = None, all_players: bool = False, min_games: int = 0,
                   result: str | None = None, session: str | None = None) -> pd.DataFrame:
    """Share of games with at least one blunder of each kind, one row per player and (context, severity, phase).

    all_players returns the benchmark: every player with at least min_games games under the shared filters (HAVING in Cube).
    result keeps only the games with that playing_result ('Win', 'Lose' or 'Draw').
    session keeps only the games of that session.
    """
    where, params = f.where(start=start, all_players=all_players, session=session)
    if result:
        where, params["result"] = where + " AND playing_result = :result", result
    having = ""
    if min_games:
        having, params["min_games"] = "HAVING MEASURE(nb_games_played) >= :min_games", min_games
    measures = ", ".join(f"MEASURE({m}) AS {m}" for m in BLUNDER_MEASURES.values())
    df = run(
        f"SELECT username_global, MEASURE(nb_games_played) AS games, {measures} FROM v_games {where} GROUP BY 1 {having}",
        params,
    )
    out = df.melt(id_vars=["username_global", "games"], var_name="measure", value_name="share")
    keys = pd.DataFrame(
        [(m, *k) for k, m in BLUNDER_MEASURES.items()], columns=["measure", "context", "severity", "phase"]
    )
    out = out.merge(keys, on="measure").drop(columns="measure")
    out["share"] = pd.to_numeric(out["share"], errors="coerce")
    return out


# Technique KPIs: rate measure and the count of games it is computed on (its denominator).
TECHNIQUE_KPIS = {
    "conversion": ("conversion_rate", "nb_games_decisive_advantage"),
    "save": ("save_rate", "nb_games_lost_position"),
    "early_resignation": ("early_resignation_rate", "nb_resignations"),
}


@st.cache_data(ttl="10m")
def technique_rate(f: Filters, kpi: str, start: date | None = None, all_players: bool = False,
                   min_games: int = 0, session: str | None = None) -> pd.DataFrame:
    """One technique rate per player: username_global, kpi, games (the games it is computed on), share.

    all_players returns the benchmark: every player with at least min_games games under the shared filters (HAVING in Cube).
    session keeps only the games of that session.
    """
    rate, base = TECHNIQUE_KPIS[kpi]
    where, params = f.where(start=start, all_players=all_players, session=session)
    having = ""
    if min_games:
        having, params["min_games"] = "HAVING MEASURE(nb_games_played) >= :min_games", min_games
    df = run(
        f"SELECT username_global, MEASURE({base}) AS games, MEASURE({rate}) AS share FROM v_games {where} "
        f"GROUP BY 1 {having}",
        params,
    )
    df["games"] = pd.to_numeric(df["games"]).fillna(0).astype(int)
    df["share"] = pd.to_numeric(df["share"], errors="coerce")
    return df.assign(kpi=kpi)


# Clock KPIs: the average measure of each.
CLOCK_KPIS = {
    "first_big_blunder": "avg_first_big_blunder_prct_time_remaining",
    **{f"end_{p}": f"avg_prct_time_remaining_playing_{p}" for p in ("early", "mid", "late")},
}


@st.cache_data(ttl="10m")
def clock_rate(f: Filters, kpi: str, start: date | None = None, all_players: bool = False,
               min_games: int = 0, session: str | None = None) -> pd.DataFrame:
    """One clock rate per player: username_global, kpi, games (games played), share.

    all_players returns the benchmark: every player with at least min_games games under the shared filters (HAVING in Cube).
    session keeps only the games of that session.
    """
    rate = CLOCK_KPIS[kpi]
    where, params = f.where(start=start, all_players=all_players, session=session)
    having = ""
    if min_games:
        having, params["min_games"] = "HAVING MEASURE(nb_games_played) >= :min_games", min_games
    df = run(
        f"SELECT username_global, MEASURE(nb_games_played) AS games, MEASURE({rate}) AS share FROM v_games {where} "
        f"GROUP BY 1 {having}",
        params,
    )
    df["games"] = pd.to_numeric(df["games"]).fillna(0).astype(int)
    df["share"] = pd.to_numeric(df["share"], errors="coerce")
    return df.assign(kpi=kpi)


# Openings: the hierarchy from the broadest family to the exact first 7 moves.
OPENING_LEVELS = ["opening_level_1_name", "opening_level_2_name", "opening_level_7_name", "opener_7_moves"]
SCORE_TURNS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]


def _with_colour(where: str, params: dict, playing_as: str | None) -> tuple[str, dict]:
    if playing_as:
        where, params["playing_as"] = where + " AND playing_as = :playing_as", playing_as
    return where, params


@st.cache_data(ttl="10m")
def opening_tree(f: Filters, playing_as: str | None, start: date | None = None,
                 session: str | None = None) -> pd.DataFrame:
    """Games and win rate per opening path (OPENING_LEVELS). start or session keeps the recent games only."""
    where, params = _with_colour(*f.where(start=start, session=session), playing_as)
    cols = ", ".join(OPENING_LEVELS)
    df = run(
        f"SELECT {cols}, MEASURE(nb_games_played) AS games, MEASURE(win_rate) AS win_rate FROM v_games {where} "
        f"GROUP BY {', '.join(str(i + 1) for i in range(len(OPENING_LEVELS)))}",
        params,
    )
    df["games"] = pd.to_numeric(df["games"]).fillna(0).astype(int)
    df["win_rate"] = pd.to_numeric(df["win_rate"], errors="coerce")
    df[OPENING_LEVELS] = df[OPENING_LEVELS].fillna("Unknown")
    return df


@st.cache_data(ttl="10m")
def opening_games(f: Filters, playing_as: str | None) -> pd.DataFrame:
    """One row per game of the selected player: its opening, result and evaluation every 5 moves."""
    where, params = _with_colour(*f.where(), playing_as)
    scores = ", ".join(f"score_playing_turn_{t}" for t in SCORE_TURNS)
    df = run(
        f"SELECT end_time, url, time_class, playing_as, playing_result, playing_rating, opponent_rating, eco, "
        f"{', '.join(OPENING_LEVELS)}, {scores} FROM v_games {where} ORDER BY end_time DESC",
        params,
    )
    df[OPENING_LEVELS] = df[OPENING_LEVELS].fillna("Unknown")
    return df


# ---------- Summary page ----------
@st.cache_data(ttl="10m")
def results(f: Filters, start: date | None = None, session: str | None = None) -> pd.Series:
    """Games, wins, draws, losses and win rate of the selected player."""
    where, params = f.where(start=start, session=session)
    df = run(f"SELECT {RESULT_MEASURES} FROM v_games {where}", params)
    out = df.iloc[0] if not df.empty else pd.Series({"games": 0})
    return pd.to_numeric(out, errors="coerce").fillna({"games": 0, "wins": 0, "draws": 0, "losses": 0})


@st.cache_data(ttl="10m")
def opening_results(f: Filters, start: date | None = None, session: str | None = None) -> pd.DataFrame:
    """Results per colour and opening (opening_level_2_name)."""
    where, params = f.where(start=start, session=session)
    df = run(f"SELECT playing_as, opening_level_2_name AS opening, {RESULT_MEASURES} FROM v_games {where} GROUP BY 1, 2",
             params)
    df["opening"] = df["opening"].fillna("Unknown")
    for col in ("games", "wins", "draws", "losses"):
        df[col] = pd.to_numeric(df[col]).fillna(0).astype(int)
    df["win_rate"] = pd.to_numeric(df["win_rate"], errors="coerce")
    return df


@st.cache_data(ttl="10m")
def games_detail(f: Filters, start: date | None = None, session: str | None = None) -> pd.DataFrame:
    """One row per game of the selected player, oldest first: what is needed to pick the games to review."""
    where, params = f.where(start=start, session=session)
    df = run(
        "SELECT end_time, url, time_class, playing_as, playing_result, playing_result_detailed, playing_rating, "
        "opponent_rating, rating_gap_category, opening_level_2_name, opening_level_7_name, nb_moves, "
        "max_score_playing, min_score_playing, final_score_playing, nb_blunder_big_blunder_playing, "
        "first_big_blunder_playing_prct_time_remaining, first_throw_big_blunder_playing_prct_time_remaining, "
        f"first_miss_opp_big_blunder_playing_prct_time_remaining FROM v_games {where} ORDER BY end_time",
        params,
    )
    df["end_time"] = pd.to_datetime(df["end_time"])
    return df
