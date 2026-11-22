"""Altair charts for the v2 app. They only draw what cube.py returns."""
from __future__ import annotations

import altair as alt
import pandas as pd

TIME_CLASS_COLOURS = {"bullet": "#f58518", "blitz": "#e45756", "rapid": "#4c78a8", "daily": "#54a24b"}
TREND_COLOURS = {"Better": "#2e9e5b", "Worse": "#d1495b", "No change": "#9aa0a6"}
WIN_RATE_SCALE = alt.Scale(scheme="redyellowgreen", domain=[0.2, 0.8], domainMid=0.5, clamp=True)
GREY = "#9aa0a6"
RECENT_COLOUR = "#4c78a8"
ROW_HEIGHT = 30


def elo_trend(df: pd.DataFrame, grain: str) -> alt.Chart:
    tcs = [t for t in TIME_CLASS_COLOURS if t in set(df["time_class"])] + sorted(set(df["time_class"]) - set(TIME_CLASS_COLOURS))
    colour = alt.Scale(domain=tcs, range=[TIME_CLASS_COLOURS.get(t, GREY) for t in tcs])
    return (
        alt.Chart(df)
        .mark_line(point=alt.OverlayMarkDef(size=28), strokeWidth=2)
        .encode(
            x=alt.X("period:T", title=None),
            y=alt.Y("avg_rating:Q", title="Average ELO", scale=alt.Scale(zero=False)),
            color=alt.Color("time_class:N", scale=colour, title=None, legend=alt.Legend(orient="top")),
            tooltip=[
                alt.Tooltip("time_class:N", title="Time class"),
                alt.Tooltip("period:T", title="Week of" if grain == "week" else "Day"),
                alt.Tooltip("avg_rating:Q", title="Average ELO", format=",.0f"),
                alt.Tooltip("games:Q", title="Games"),
            ],
        )
        .properties(height=300)
    )


def _size_legend_values(max_games: int) -> list[int]:
    """Three readable sizes for the legend: about a quarter, half and all of the largest square."""
    if max_games <= 3:
        return list(range(1, max_games + 1))
    step = 5 if max_games >= 20 else 1
    return sorted({max(1, round(max_games * f / step) * step) for f in (0.25, 0.5)} | {max_games})


def _heatmap_panel(df: pd.DataFrame, lo: int, hi: int, max_games: int, size: int, title: str) -> alt.LayerChart:
    n = (hi - lo) // 50 + 1
    # Cells are at most 44 px, so a matrix with few bands stays compact and its size legend fits.
    cell = min(size / n, 44)
    size = round(cell * n)
    every = max(1, int(-(-32 // cell)))  # thin labels so they never overlap
    ticks = list(range(lo, hi + 51, 50))[::every]
    domain = [lo, hi + 50]
    data = df.assign(x=df["opponent_rating_band"] + 25, y=df["playing_rating_band"] + 25)
    x = alt.X("x:Q", title="Opponent ELO →", scale=alt.Scale(domain=domain, nice=False, zero=False),
              axis=alt.Axis(values=ticks, grid=False, format="d"))
    y = alt.Y("y:Q", title="Your ELO →", scale=alt.Scale(domain=domain, nice=False, zero=False),
              axis=alt.Axis(values=ticks, grid=False, format="d"))
    diagonal = (
        alt.Chart(pd.DataFrame({"x": domain, "y": domain}))
        .mark_line(strokeDash=[4, 3], color=GREY, strokeWidth=1)
        .encode(x=x, y=y)
    )
    squares = (
        alt.Chart(data)
        .mark_square(opacity=0.9)
        .encode(
            x=x,
            y=y,
            size=alt.Size(
                "games:Q", title="Games", scale=alt.Scale(domain=[0, max_games], range=[6, (cell * 0.95) ** 2]),
                legend=alt.Legend(values=_size_legend_values(max_games), symbolFillColor=GREY, symbolStrokeColor=GREY),
            ),
            color=alt.Color("win_rate:Q", title="Win rate", scale=WIN_RATE_SCALE, legend=alt.Legend(format=".0%")),
            tooltip=[
                alt.Tooltip("playing_rating_band:Q", title="Your band from", format="d"),
                alt.Tooltip("opponent_rating_band:Q", title="Opponent band from", format="d"),
                alt.Tooltip("win_rate:Q", title="Win rate", format=".1%"),
                alt.Tooltip("wins:Q", title="Won"),
                alt.Tooltip("draws:Q", title="Drawn"),
                alt.Tooltip("losses:Q", title="Lost"),
                alt.Tooltip("games:Q", title="Games"),
            ],
        )
    )
    return (diagonal + squares).properties(width=size, height=size, title=title)


def elo_matrix(df: pd.DataFrame, split: bool) -> alt.TopLevelMixin:
    """Win rate (colour) and games (square area) by your ELO band and your opponent's, on one scale for every panel."""
    lo = int(min(df["playing_rating_band"].min(), df["opponent_rating_band"].min()))
    hi = int(max(df["playing_rating_band"].max(), df["opponent_rating_band"].max()))
    max_games = int(df["games"].max())
    # "pad" keeps each plot at its pixel size and adds axes and legends around it; the default "fit"
    # would squeeze them into that size and shrink the grid.
    pad = alt.AutoSizeParams(type="pad", contains="padding")
    if not split:
        return _heatmap_panel(df, lo, hi, max_games, 520, "All games").properties(autosize=pad)
    panels = [
        _heatmap_panel(df[df["playing_as"] == colour], lo, hi, max_games, 420, f"Playing {colour} vs {other}")
        for colour, other in (("White", "Black"), ("Black", "White"))
    ]
    return alt.hconcat(*panels).resolve_scale(size="shared", color="shared").properties(autosize=pad)


def dumbbell(df: pd.DataFrame, label_col: str, order: list[str], max_games: int,
             title: str | None = None, show_legend: bool = True) -> alt.LayerChart:
    """Win rate before (hollow) → last days (filled), one row per label, line coloured by the change.

    Every label in `order` gets a row, so two charts with the same order line up side by side.
    """
    data = df.copy()
    data["trend"] = data["change"].apply(
        lambda c: "No change" if pd.isna(c) or abs(c) < 0.01 else ("Better" if c > 0 else "Worse")
    )
    data["note"] = data.apply(
        lambda r: (f"{r['change'] * 100:+.1f} pts" if pd.notna(r["change"]) else ("only recent" if r["recent_games"] else "only before"))
        + f"  ·  {r['before_games']} → {r['recent_games']} games",
        axis=1,
    )
    y = alt.Y(f"{label_col}:N", sort=order, scale=alt.Scale(domain=order), title=None, axis=alt.Axis(labelLimit=160))
    # The axis stops at 100%; the extra room on the right holds the change labels.
    x_scale = alt.Scale(domain=[0, 1.6], nice=False)
    size_scale = alt.Scale(domain=[0, max_games], range=[25, 400])
    trend_scale = alt.Scale(domain=list(TREND_COLOURS), range=list(TREND_COLOURS.values()))
    tooltip = [
        alt.Tooltip(f"{label_col}:N", title="Row"),
        alt.Tooltip("before_win_rate:Q", title="Win rate before", format=".1%"),
        alt.Tooltip("recent_win_rate:Q", title="Win rate recent", format=".1%"),
        alt.Tooltip("change:Q", title="Change", format="+.1%"),
        alt.Tooltip("before_games:Q", title="Games before"),
        alt.Tooltip("recent_games:Q", title="Games recent"),
    ]
    base = alt.Chart(data)
    reference = base.mark_rule(strokeDash=[4, 3], color=GREY).encode(x=alt.datum(0.5))
    line = base.mark_rule(strokeWidth=3).encode(
        y=y,
        x=alt.X("before_win_rate:Q", scale=x_scale, title="Win rate", axis=alt.Axis(format=".0%", values=[0, 0.25, 0.5, 0.75, 1])),
        x2="recent_win_rate:Q",
        color=alt.Color("trend:N", title=None, scale=trend_scale, legend=alt.Legend(orient="top") if show_legend else None),
        tooltip=tooltip,
    )
    before = base.mark_point(filled=False, color=GREY, strokeWidth=1.5, opacity=1).encode(
        y=y, x=alt.X("before_win_rate:Q", scale=x_scale),
        size=alt.Size("before_games:Q", scale=size_scale, legend=None), tooltip=tooltip,
    )
    recent = base.mark_circle(color=RECENT_COLOUR, opacity=1).encode(
        y=y, x=alt.X("recent_win_rate:Q", scale=x_scale),
        size=alt.Size("recent_games:Q", scale=size_scale, legend=None), tooltip=tooltip,
    )
    notes = base.mark_text(align="left", dx=10, fontSize=11).encode(
        y=y, x=alt.datum(1.04), text="note:N", color=alt.Color("trend:N", scale=trend_scale, legend=None),
    )
    # A fixed height in pixels would include the legend, axis and title, which squashes charts with few rows:
    # give each row its own step instead.
    chart = alt.layer(reference, line, before, recent, notes).properties(height=alt.Step(ROW_HEIGHT))
    return chart.properties(title=title) if title else chart
