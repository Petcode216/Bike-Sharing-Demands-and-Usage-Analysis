"""Plotly figure builders for the dashboard.

Each function receives already-filtered tables and returns a go.Figure. The grain
(per day / per hour) is stated in each chart title or axis.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.analysis import kpis as K
from src.config import WEEKDAY_ORDER
from src.visualization.style import (DAY_TYPE_COLORS, NEUTRAL, PLOTLY_LAYOUT, SEGMENT_COLORS,
                                     SEGMENT_NAMES, SEQUENTIAL_BLUE, WEATHER_COLORS, YEAR_COLORS)

SEQ_SCALE = [[i / (len(SEQUENTIAL_BLUE) - 1), c] for i, c in enumerate(SEQUENTIAL_BLUE)]


def _layout(fig: go.Figure, title: str, height: int = 380, **kw) -> go.Figure:
    layout = {**PLOTLY_LAYOUT, **kw}
    fig.update_layout(**layout, title={"text": title, "x": 0, "xanchor": "left", "font": {"size": 15}},
                      height=height)
    return fig


def empty(msg: str = "No data for the current filters") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font={"size": 14, "color": NEUTRAL})
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _layout(fig, "", height=300)


def daily_trend(day: pd.DataFrame, segments: list[str]) -> go.Figure:
    # Reindex to every calendar day so filtered-out days become gaps, not bridged lines.
    full = pd.date_range(day["dteday"].min(), day["dteday"].max(), freq="D")
    d = day.set_index("dteday").reindex(full).rename_axis("dteday").reset_index()
    fig = go.Figure()
    for seg in segments:
        roll = d.set_index("dteday")[seg].rolling(7, min_periods=4, center=True).mean()
        fig.add_scatter(x=d["dteday"], y=d[seg], mode="lines", line={"width": 0.8, "color": SEGMENT_COLORS[seg]},
                        opacity=0.25, name=f"{SEGMENT_NAMES[seg]} (daily)", showlegend=False,
                        hovertemplate="%{x|%a %d %b %Y}<br>" + SEGMENT_NAMES[seg] + ": %{y:,}<extra></extra>")
        fig.add_scatter(x=roll.index, y=roll.values, mode="lines", line={"width": 2, "color": SEGMENT_COLORS[seg]},
                        name=f"{SEGMENT_NAMES[seg]} (7-day mean)",
                        hovertemplate="%{x|%d %b %Y}<br>7-day mean: %{y:,.0f}<extra></extra>")
    fig.update_yaxes(title="Rentals per day")
    return _layout(fig, "Daily rentals (filtered days only; gaps = excluded days)", hovermode="x unified")


def monthly_stacked(day: pd.DataFrame, segments: list[str]) -> go.Figure:
    m = day.groupby("year_month")[["registered", "casual", "cnt"]].sum().reset_index()
    fig = go.Figure()
    stack = [s for s in ["registered", "casual"] if s in segments] or ["cnt"]
    for seg in stack:
        fig.add_bar(x=m["year_month"], y=m[seg], name=SEGMENT_NAMES[seg], marker_color=SEGMENT_COLORS[seg],
                    hovertemplate="%{x|%b %Y}<br>" + SEGMENT_NAMES[seg] + ": %{y:,}<extra></extra>")
    fig.update_layout(barmode="stack", bargap=0.15)
    fig.update_yaxes(title="Rentals per month (filtered days)")
    return _layout(fig, "Monthly rentals by user type")


def hourly_by_daytype(hour: pd.DataFrame, seg: str) -> go.Figure:
    prof = K.hourly_profile(hour, by="day_type")
    col = {"cnt": "mean_cnt", "casual": "mean_casual", "registered": "mean_registered"}[seg]
    fig = go.Figure()
    for dt, g in prof.groupby("day_type", observed=True):
        fig.add_scatter(x=g["hr"], y=g[col], mode="lines+markers", name=str(dt),
                        line={"width": 2, "color": DAY_TYPE_COLORS[str(dt)]}, marker={"size": 7},
                        customdata=np.stack([g["hours"], g["p10_cnt"], g["p90_cnt"]], axis=1),
                        hovertemplate=(f"<b>{dt}</b> %{{x}}:00<br>Mean {SEGMENT_NAMES[seg].lower()}: %{{y:,.0f}}/h"
                                       "<br>Total p10-p90: %{customdata[1]:,.0f}-%{customdata[2]:,.0f}"
                                       "<br>Observed hours: %{customdata[0]}<extra></extra>"))
    fig.update_xaxes(title="Hour of day", dtick=2)
    fig.update_yaxes(title="Mean rentals per hour")
    return _layout(fig, f"Hourly profile by day type - {SEGMENT_NAMES[seg]} (grain: per hour)")


def hour_weekday_heatmap(hour: pd.DataFrame, seg: str) -> go.Figure:
    mat = K.hour_weekday_matrix(hour, value=seg).reindex(WEEKDAY_ORDER).dropna(how="all")
    fig = go.Figure(go.Heatmap(z=mat.values, x=mat.columns, y=mat.index.astype(str), colorscale=SEQ_SCALE,
                               xgap=2, ygap=2, colorbar={"title": "Mean/h"},
                               hovertemplate="%{y} %{x}:00<br>Mean rentals: %{z:,.0f}/h<extra></extra>"))
    fig.update_xaxes(title="Hour of day", dtick=2, showgrid=False)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return _layout(fig, f"Mean rentals per hour - weekday x hour ({SEGMENT_NAMES[seg]})", height=340)


def temperature_scatter(day: pd.DataFrame, seg: str) -> go.Figure:
    fig = go.Figure()
    for yr, g in day.groupby("year"):
        fig.add_scatter(x=g["temp_c"], y=g[seg], mode="markers", name=str(yr),
                        marker={"size": 8, "color": YEAR_COLORS[yr], "opacity": 0.65,
                                "line": {"width": 1, "color": "white"}},
                        customdata=np.stack([g["dteday"].dt.strftime("%d %b %Y"), g["weather_group"].astype(str)], 1),
                        hovertemplate="%{customdata[0]}<br>%{x:.1f} °C, %{customdata[1]}<br>"
                                      "Rentals: %{y:,}<extra></extra>")
    fig.update_xaxes(title="Daily mean temperature (°C)")
    fig.update_yaxes(title=f"{SEGMENT_NAMES[seg]} rentals per day")
    return _layout(fig, "Temperature vs daily rentals (grain: per day)")


def weather_bars(day: pd.DataFrame, segments: list[str]) -> go.Figure:
    ws = day.groupby("weather_group", observed=True)[["cnt", "casual", "registered"]].mean()
    n = day.groupby("weather_group", observed=True).size()
    fig = go.Figure()
    for seg in segments:
        fig.add_bar(x=ws.index.astype(str), y=ws[seg], name=SEGMENT_NAMES[seg], marker_color=SEGMENT_COLORS[seg],
                    customdata=n.values,
                    hovertemplate="%{x}<br>Mean " + SEGMENT_NAMES[seg].lower() + ": %{y:,.0f}/day"
                                  "<br>Days: %{customdata}<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08)
    fig.update_yaxes(title="Mean rentals per day")
    return _layout(fig, "Mean daily rentals by weather (grain: per day)")


def env_scatter(day: pd.DataFrame, var: str, label: str, seg: str) -> go.Figure:
    sub = day.dropna(subset=[var])
    fig = go.Figure()
    for wg, g in sub.groupby("weather_group", observed=True):
        fig.add_scatter(x=g[var], y=g[seg], mode="markers", name=str(wg),
                        marker={"size": 7, "color": WEATHER_COLORS[str(wg)], "opacity": 0.6,
                                "line": {"width": 1, "color": "white"}},
                        hovertemplate=f"{label}: %{{x:.1f}}<br>Rentals: %{{y:,}}<extra>{wg}</extra>")
    rho = sub[[var, seg]].corr(method="spearman").iloc[0, 1] if len(sub) > 2 else float("nan")
    fig.update_xaxes(title=label)
    fig.update_yaxes(title="Rentals per day")
    return _layout(fig, f"{label.split(' (')[0]} vs daily rentals (Spearman ρ = {rho:.2f})", height=340)


def segment_hourly(hour: pd.DataFrame) -> go.Figure:
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, subplot_titles=("Working days", "Non-working days"))
    for col, flag in [(1, 1), (2, 0)]:
        g = hour[hour["workingday"] == flag]
        if g.empty:
            continue
        prof = g.groupby("hr")[["registered", "casual"]].mean()
        for seg in ["registered", "casual"]:
            fig.add_scatter(x=prof.index, y=prof[seg], mode="lines+markers", name=SEGMENT_NAMES[seg],
                            line={"width": 2, "color": SEGMENT_COLORS[seg]}, marker={"size": 6},
                            showlegend=col == 1, legendgroup=seg,
                            hovertemplate="%{x}:00<br>" + SEGMENT_NAMES[seg] + ": %{y:,.0f}/h<extra></extra>",
                            row=1, col=col)
    fig.update_xaxes(title="Hour of day", dtick=3)
    fig.update_yaxes(title="Mean rentals per hour", col=1)
    _layout(fig, "Casual vs registered by hour (grain: per hour)")
    fig.update_xaxes(gridcolor=PLOTLY_LAYOUT["xaxis"]["gridcolor"])
    fig.update_yaxes(gridcolor=PLOTLY_LAYOUT["yaxis"]["gridcolor"])
    return fig


def casual_share_monthly(day: pd.DataFrame) -> go.Figure:
    m = day.groupby("year_month")[["casual", "cnt"]].sum()
    share = m["casual"] / m["cnt"]
    fig = go.Figure(go.Scatter(x=share.index, y=share, mode="lines+markers", name="Casual share",
                               line={"width": 2, "color": SEGMENT_COLORS["casual"]}, marker={"size": 7},
                               hovertemplate="%{x|%b %Y}<br>Casual share: %{y:.1%}<extra></extra>"))
    fig.update_yaxes(title="Casual share of rentals", tickformat=".0%", rangemode="tozero")
    return _layout(fig, "Casual share of monthly rentals")


def weekday_mix(day: pd.DataFrame) -> go.Figure:
    s = K.daily_summary_by(day, "weekday_label")
    fig = go.Figure()
    for seg, col in [("registered", "mean_registered"), ("casual", "mean_casual")]:
        fig.add_bar(x=s.index.astype(str), y=s[col], name=SEGMENT_NAMES[seg], marker_color=SEGMENT_COLORS[seg],
                    customdata=s["casual_share"],
                    hovertemplate="%{x}<br>" + SEGMENT_NAMES[seg] + ": %{y:,.0f}/day"
                                  "<br>Casual share: %{customdata:.0%}<extra></extra>")
    fig.update_layout(barmode="stack", bargap=0.3)
    fig.update_yaxes(title="Mean rentals per day")
    return _layout(fig, "Weekday user mix (grain: per day)")


def demand_tiers(hour: pd.DataFrame) -> go.Figure:
    w = K.demand_windows(hour)
    tiers = ["Low", "Moderate", "High", "Consistently high"]
    w["code"] = w["tier"].map({t: i for i, t in enumerate(tiers)})
    z = w.pivot(index="day_type", columns="hr", values="code")
    mean = w.pivot(index="day_type", columns="hr", values="mean_cnt")
    tier_txt = w.pivot(index="day_type", columns="hr", values="tier")
    scale = []
    cols = [SEQUENTIAL_BLUE[0], SEQUENTIAL_BLUE[2], SEQUENTIAL_BLUE[4], SEQUENTIAL_BLUE[6]]
    for i, c in enumerate(cols):
        scale += [[i / 4, c], [(i + 1) / 4, c]]
    fig = go.Figure(go.Heatmap(
        z=z.values, x=z.columns, y=z.index.astype(str), zmin=-0.5, zmax=3.5, colorscale=scale, xgap=2, ygap=2,
        text=mean.round(0).values, texttemplate="%{text:.0f}", textfont={"size": 10},
        customdata=tier_txt.values,
        colorbar={"tickvals": [0, 1, 2, 3], "ticktext": tiers, "title": "Tier"},
        hovertemplate="%{y} %{x}:00<br>Mean: %{text:,.0f} rentals/h<br>Tier: %{customdata}<extra></extra>"))
    fig.update_xaxes(title="Hour of day", dtick=1, showgrid=False)
    fig.update_yaxes(showgrid=False, autorange="reversed")
    return _layout(fig, "Demand tiers by hour and day type (cell = mean rentals per hour)", height=320)
