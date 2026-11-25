"""Altair charts for the v2 app. They only draw what cube.py returns."""
from __future__ import annotations

import math
import zlib

import altair as alt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

TIME_CLASS_COLOURS = {"bullet": "#f58518", "blitz": "#e45756", "rapid": "#4c78a8", "daily": "#54a24b"}
TREND_COLOURS = {"Better": "#2e9e5b", "Worse": "#d1495b", "No change": "#9aa0a6"}
NEUTRAL_CHANGE_COLOUR = "#8e6cc9"  # a change on a rate with no better side
WIN_RATE_SCALE = alt.Scale(scheme="redyellowgreen", domain=[0.2, 0.8], domainMid=0.5, clamp=True)
GREY = "#9aa0a6"
RECENT_COLOUR = "#4c78a8"
ROW_HEIGHT = 30
YOU_COLOUR = RECENT_COLOUR
BOX_COLOUR = "#c9cdd2"
DISTRIBUTION_ROW_HEIGHT = 76


def elo_trend(df: pd.DataFrame) -> alt.Chart:
    """ELO after each game, one line per time class; small points so that thousands of games stay readable."""
    tcs = [t for t in TIME_CLASS_COLOURS if t in set(df["time_class"])] + sorted(set(df["time_class"]) - set(TIME_CLASS_COLOURS))
    colour = alt.Scale(domain=tcs, range=[TIME_CLASS_COLOURS.get(t, GREY) for t in tcs])
    return (
        alt.Chart(df)
        .mark_line(point=alt.OverlayMarkDef(size=10), strokeWidth=1.5, interpolate="monotone")
        .encode(
            x=alt.X("end_time:T", title=None),
            y=alt.Y("playing_rating:Q", title="ELO", scale=alt.Scale(zero=False)),
            color=alt.Color("time_class:N", scale=colour, title=None, legend=alt.Legend(orient="top")),
            tooltip=[
                alt.Tooltip("time_class:N", title="Time class"),
                alt.Tooltip("end_time:T", title="Game ended", format="%d %b %Y %H:%M"),
                alt.Tooltip("playing_rating:Q", title="ELO", format=",.0f"),
                alt.Tooltip("playing_result:N", title="Result"),
                alt.Tooltip("opponent_rating:Q", title="Opponent ELO", format=",.0f"),
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


def _share_ticks(bottom: float, top: float) -> list[float]:
    """At most 6 round ticks covering [bottom, top]; they start at 0% unless the values sit well above it."""
    bottom = 0 if bottom < (top - bottom) else bottom  # keep the zero baseline when it costs little room
    step = next((s for s in (0.01, 0.02, 0.05, 0.1, 0.2, 0.25) if (top - bottom) / s <= 5), 0.25)
    lo = math.floor(bottom / step + 1e-9)
    return [round(i * step, 4) for i in range(lo, max(lo + 1, math.ceil(top / step - 1e-9)) + 1)]


def peer_distribution(peers: pd.DataFrame, you: pd.DataFrame, text_colour: str, axis_title: str | None) -> alt.LayerChart:
    """A rate for you against the other players, on one row with its own x scale (built by benchmark.compare).

    peers: username_global, games, row, share. The other players: grey box (min, quartiles, max) and one dot each.
    you: one row with row, whole, whole_games, recent, recent_games, change, trend, better_than, label.
    Your share over the whole period (blue bar), then an arrow to the recent days: it points the way the share moved
    and is green when that is better for you (trend), red otherwise. `label` is written on the right.
    """
    peers = peers.assign(
        jitter=peers["username_global"].map(lambda u: zlib.crc32(u.encode()) % 1000 / 1000 - 0.5)
    )
    you = you.assign(angle=you["change"].apply(lambda c: 270 if pd.notna(c) and c < 0 else 90))
    values = pd.concat([peers["share"], you["whole"], you["recent"]]).dropna()
    ticks = _share_ticks(values.min() if not values.empty else 0, max(values.max() if not values.empty else 0, 0.01))
    span = (ticks[-1] - ticks[0]) * 1.9
    # The axis stops at the last tick; the extra room on the right holds the label.
    x_scale = alt.Scale(domain=[ticks[0], ticks[0] + span], nice=False)
    # The head needs a shaft of about 20 px; the plot is roughly 380 px wide, so shorter arrows show the dot only.
    you = you.assign(head=you["change"].abs() / span * 380 >= 20)
    x_axis = alt.Axis(format=".0%", values=ticks, title=axis_title)
    y = alt.Y("row:N", title=None, axis=alt.Axis(labelLimit=170))
    trend_scale = alt.Scale(domain=["Better", "Worse", "Change"],
                            range=[TREND_COLOURS["Better"], TREND_COLOURS["Worse"], NEUTRAL_CHANGE_COLOUR])
    you_tooltip = [
        alt.Tooltip("row:N", title="Row"),
        alt.Tooltip("whole:Q", title="You, whole period", format=".1%"),
        alt.Tooltip("whole_games:Q", title="Games, whole period"),
        alt.Tooltip("recent:Q", title="You, recent days", format=".1%"),
        alt.Tooltip("recent_games:Q", title="Games, recent days"),
        alt.Tooltip("change:Q", title="Change", format="+.1%"),
        alt.Tooltip("better_than:Q", title="Better than (or above) this share of players", format=".0%"),
    ]

    layers = []
    if not peers.empty:
        peer_base = alt.Chart(peers)
        layers += [
            peer_base.mark_boxplot(extent="min-max", size=28, color=BOX_COLOUR, opacity=0.55,
                                   median={"color": GREY, "strokeWidth": 2}, rule={"color": GREY},
                                   ticks=False, outliers=False)
            .encode(x=alt.X("share:Q", scale=x_scale, axis=x_axis), y=y),
            peer_base.mark_circle(size=28, color=GREY, opacity=0.6).encode(
                x=alt.X("share:Q", scale=x_scale),
                y=y,
                yOffset=alt.YOffset("jitter:Q", scale=alt.Scale(domain=[-0.9, 0.9])),
                tooltip=[alt.Tooltip("username_global:N", title="Player"),
                         alt.Tooltip("share:Q", title="Rate", format=".1%"),
                         alt.Tooltip("games:Q", title="Games counted")],
            ),
        ]
    base = alt.Chart(you)
    trend = alt.Color("trend:N", scale=trend_scale, legend=None)
    layers += [
        base.mark_tick(thickness=4, size=40, color=YOU_COLOUR, opacity=1).encode(
            x=alt.X("whole:Q", scale=x_scale, axis=x_axis), y=y, tooltip=you_tooltip,
        ),
        # Arrow: shaft from the whole period to the recent days, head pointing the way the share moved.
        base.mark_rule(strokeWidth=3).encode(
            x=alt.X("whole:Q", scale=x_scale), x2="recent:Q", y=y, color=trend, tooltip=you_tooltip,
        ),
        # Head just before the dot (offset in pixels, towards where the arrow comes from), then the dot on the exact value.
        *[
            base.transform_filter(f"datum.angle == {angle} && datum.head")
            .mark_point(shape="triangle", filled=True, size=130, opacity=1, strokeWidth=0, xOffset=offset)
            .encode(x=alt.X("recent:Q", scale=x_scale), y=y, color=trend,
                    angle=alt.Angle("angle:Q", scale=None), tooltip=you_tooltip)
            for angle, offset in ((90, -11), (270, 11))
        ],
        base.mark_circle(size=70, opacity=1, stroke="white", strokeWidth=1).encode(
            x=alt.X("recent:Q", scale=x_scale), y=y, color=trend, tooltip=you_tooltip,
        ),
        base.mark_text(align="left", baseline="middle", lineBreak="\n", fontSize=12, lineHeight=16,
                       color=text_colour).encode(
            x=alt.datum(ticks[-1] + span * 0.03), y=y, text="label:N",
        ),
    ]
    return alt.layer(*layers).properties(height=alt.Step(DISTRIBUTION_ROW_HEIGHT))


def opening_sunburst(tree: pd.DataFrame, levels: list[str]) -> go.Figure:
    """Openings as rings, from the family (centre) to the exact first moves (outside).

    Size: games played. Colour: win rate, red below 50%, green above (a parent gets the games-weighted average).
    """
    df = tree[tree["games"] > 0].assign(win_rate=lambda d: d["win_rate"].fillna(0.5))
    fig = px.sunburst(
        df, path=levels, values="games", color="win_rate",
        color_continuous_scale="RdYlGn", color_continuous_midpoint=0.5, range_color=[0.2, 0.8],
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>%{value} games<br>Win rate %{color:.0%}<extra></extra>",
        insidetextorientation="radial",
    )
    fig.update_layout(height=620, margin=dict(l=0, r=0, t=10, b=0), coloraxis_showscale=False,
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig


# Evaluation colours: red when you are worse, grey when balanced, green when you are better (centipawns).
SCORE_SCALE = alt.Scale(domain=[-300, -100, -25, 25, 100, 300], interpolate="rgb", clamp=True,
                        range=["#c0182b", "#e8534f", "#a8adb3", "#a8adb3", "#3cb371", "#0f8a3c"])


def score_by_move(games: pd.DataFrame, turns: list[int], title: str) -> alt.LayerChart:
    """Evaluation after every 5 moves over the games of one opening.

    Box per move coloured by its median (red: you are worse, green: you are better), median as a line,
    red / green background below / above 0.
    """
    long = games.melt(value_vars=[f"score_playing_turn_{t}" for t in turns], var_name="turn", value_name="score")
    long = long.dropna(subset=["score"])
    long["move"] = long["turn"].str.rsplit("_", n=1).str[-1].astype(int)
    long["median"] = long.groupby("move")["score"].transform("median")
    x = alt.X("move:O", title="Move", axis=alt.Axis(labelAngle=0))
    y_scale = alt.Scale(domain=[-1000, 1000])
    colour = alt.Color("median:Q", scale=SCORE_SCALE, legend=None)

    bands = alt.Chart(pd.DataFrame({"lo": [0, -1000], "hi": [1000, 0], "c": ["#2e9e5b", "#d1495b"]})).mark_rect(
        opacity=0.07).encode(y=alt.Y("lo:Q", scale=y_scale), y2="hi:Q", color=alt.Color("c:N", scale=None))
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=GREY, opacity=0.6).encode(y="y:Q")
    boxes = alt.Chart(long).mark_boxplot(extent=1.5, outliers=False, size=22, opacity=0.9,
                                        median={"color": "white", "strokeWidth": 2},
                                        rule={"color": GREY, "opacity": 0.6}, ticks=False).encode(
        x=x, y=alt.Y("score:Q", title="Evaluation (centipawns)", scale=y_scale), color=colour,
    )
    medians = long.drop_duplicates("move").assign(games=lambda d: d["move"].map(long.groupby("move").size()))
    line = alt.Chart(medians).mark_line(color=GREY, strokeWidth=1.5, strokeDash=[4, 3], interpolate="monotone").encode(
        x=x, y=alt.Y("median:Q", scale=y_scale))
    points = alt.Chart(medians).mark_point(shape="diamond", size=110, filled=True, opacity=1,
                                           stroke="white", strokeWidth=1).encode(
        x=x, y=alt.Y("median:Q", scale=y_scale), color=colour,
        tooltip=[alt.Tooltip("move:O", title="Move"), alt.Tooltip("median:Q", title="Median", format="+.0f"),
                 alt.Tooltip("games:Q", title="Games")],
    )
    return (bands + zero + boxes + line + points).properties(
        height=280, title=alt.TitleParams(title, anchor="start", fontSize=13))
