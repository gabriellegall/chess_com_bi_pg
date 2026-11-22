"""Cube SQL API access for the v2 app.

Every number shown in the app is a MEASURE() of the Cube view v_games, and every
filter is pushed to Cube as a WHERE (or HAVING) clause: pandas only merges and reshapes.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta
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
# A "blunder" here excludes big blunders: each move counts in one severity only.
BLUNDER_CONTEXTS = ("throw", "miss_opp")
BLUNDER_SEVERITIES = ("blunder", "big_blunder")
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

    def where(self, start: date | None = None, end: date | None = None, all_players: bool = False) -> tuple[str, dict]:
        """all_players drops the player filter and keeps the others: the peers of the selected player."""
        start = self.start if start is None else start
        end = self.end if end is None else end
        clauses = [
            "playing_rating BETWEEN :elo_lo AND :elo_hi",
            "opponent_rating BETWEEN :opp_lo AND :opp_hi",
            "end_time >= :start",
            "end_time < :end_excl",
        ]
        params = {
            "elo_lo": self.elo[0], "elo_hi": self.elo[1],
            "opp_lo": self.opp_elo[0], "opp_hi": self.opp_elo[1],
            "start": start.isoformat(), "end_excl": (end + timedelta(days=1)).isoformat(),
        }
        if not all_players:
            clauses.insert(0, "username_global = :player")
            params["player"] = self.player
        if self.time_classes:
            clauses.append("time_class IN :time_classes")
            params["time_classes"] = list(self.time_classes)
        return "WHERE " + " AND ".join(clauses), params


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
def elo_trend(f: Filters, grain: str) -> pd.DataFrame:
    if grain not in {"day", "week"}:
        raise ValueError(grain)
    where, params = f.where()
    return run(
        f"SELECT time_class, DATE_TRUNC('{grain}', end_time) AS period, MEASURE(avg_playing_rating) AS avg_rating, "
        f"MEASURE(nb_games_played) AS games FROM v_games {where} GROUP BY 1, 2 ORDER BY 2",
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


def _periods(f: Filters, cutoff: date) -> dict[str, tuple[date, date]]:
    """Before = from the filter start to the day before the cutoff; recent = from the cutoff to the filter end."""
    return {
        "before": (f.start, min(f.end, cutoff - timedelta(days=1))),
        "recent": (max(f.start, cutoff), f.end),
    }


@st.cache_data(ttl="10m")
def progression_summary(f: Filters, cutoff: date) -> pd.DataFrame:
    rows = []
    for period, (start, end) in _periods(f, cutoff).items():
        row = {"period": period, "games": 0, "win_rate": None, "avg_rating": None, "avg_opponent_rating": None}
        if start <= end:
            where, params = f.where(start, end)
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
def progression(f: Filters, cutoff: date, dimension: str, split: bool) -> pd.DataFrame:
    """Results before vs recent, one row per dimension value (and colour when split), with the win rate change."""
    if dimension not in PROGRESSION_DIMENSIONS:
        raise ValueError(dimension)
    dims = (["playing_as"] if split else []) + [dimension]
    frames = []
    for period, (start, end) in _periods(f, cutoff).items():
        if start > end:
            continue
        where, params = f.where(start, end)
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
                   result: str | None = None) -> pd.DataFrame:
    """Share of games with at least one blunder of each kind, one row per player and (context, severity, phase).

    all_players returns every player matching the other filters with at least min_games games (HAVING in Cube).
    result keeps only the games with that playing_result ('Win', 'Lose' or 'Draw').
    """
    where, params = f.where(start=start, all_players=all_players)
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
                   min_games: int = 0) -> pd.DataFrame:
    """One technique rate per player: username_global, kpi, games (the games it is computed on), share.

    all_players returns every player matching the other filters with at least min_games such games (HAVING in Cube).
    """
    rate, base = TECHNIQUE_KPIS[kpi]
    where, params = f.where(start=start, all_players=all_players)
    having = ""
    if min_games:
        having, params["min_games"] = f"HAVING MEASURE({base}) >= :min_games", min_games
    df = run(
        f"SELECT username_global, MEASURE({base}) AS games, MEASURE({rate}) AS share FROM v_games {where} "
        f"GROUP BY 1 {having}",
        params,
    )
    df["games"] = pd.to_numeric(df["games"]).fillna(0).astype(int)
    df["share"] = pd.to_numeric(df["share"], errors="coerce")
    return df.assign(kpi=kpi)
