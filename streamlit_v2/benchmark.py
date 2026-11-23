"""You against the other players: the summary rows behind charts.peer_distribution, shared by the pages."""
from __future__ import annotations

import pandas as pd

# The benchmark: every other player with at least MIN_GAMES games under the shared filters (time class, both ELO
# ranges), over all dates. The game end date and the recent period apply to the selected player only.
MIN_GAMES = 30
SCOPE = (f"every other player with at least {MIN_GAMES} games under the same time class and ELO ranges, "
         "over all their games (the game end date applies to you only)")


def pct(value: float) -> str:
    return "—" if pd.isna(value) else f"{value:.0%}" if value >= 0.1 else f"{value:.1%}"


def compare(others: pd.DataFrame, whole: pd.DataFrame, recent: pd.DataFrame, key: str, *,
            higher_is_better: bool | None, unit: str, period: str, has_recent: bool) -> pd.DataFrame:
    """Your rate over the whole period and the recent period, your rank among the others and a two-line label.

    period labels the recent period, e.g. "Last 90 days" or "Last session".
    higher_is_better None: the rate has no better side (trend "Change", rank = share of the others below you).

    others: key, share (one row per other player). whole, recent: key, share, games (your rows).
    Returns one row per key: whole, whole_games, recent, recent_games, change, trend (Better / Worse),
    better_than (share of the others you beat, ties count half) and label.
    """
    you = (
        whole[[key, "share", "games"]].rename(columns={"share": "whole", "games": "whole_games"})
        .merge(recent[[key, "share", "games"]].rename(columns={"share": "recent", "games": "recent_games"}),
               on=key, how="left")
    )
    you["recent_games"] = you["recent_games"].fillna(0).astype(int)
    you["change"] = you["recent"] - you["whole"]
    sign = -1 if higher_is_better is False else 1
    you["trend"] = (
        "Change" if higher_is_better is None
        else you["change"].apply(lambda c: "Better" if pd.notna(c) and sign * c > 0 else "Worse")
    )

    def better_than(r: pd.Series) -> float:
        s = others.loc[others[key] == r[key], "share"].dropna()
        if s.empty or pd.isna(r["whole"]):
            return float("nan")
        beaten = (s > r["whole"]).sum() if higher_is_better is False else (s < r["whole"]).sum()
        return (beaten + 0.5 * (s == r["whole"]).sum()) / len(s)

    you["better_than"] = you.apply(better_than, axis=1) if not you.empty else pd.Series(dtype=float)

    def label(r: pd.Series) -> str:
        first = f"{pct(r['whole'])} {unit}"
        if pd.notna(r["better_than"]):
            first += f" · {'more' if higher_is_better is None else 'better'} than {r['better_than']:.0%}"
        if not has_recent:
            return first
        if not r["recent_games"]:
            return f"{first}\n{period}: no games"
        if pd.isna(r["recent"]):
            return f"{first}\n{period}: —"
        return f"{first}\n{period}: {pct(r['recent'])} ({round(r['change'] * 100, 1) + 0:+.1f} pts)"

    you["label"] = you.apply(label, axis=1) if not you.empty else pd.Series(dtype=str)
    return you
