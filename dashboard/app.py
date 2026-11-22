"""Interactive dashboard: Bike Sharing Demand & Usage Patterns.

Run from the project root:  python dashboard/app.py   (then open http://127.0.0.1:8050)
Reads the processed tables in data/processed/ (built by `python -m src.pipeline`).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
from dash import Dash, Input, Output, dash_table, dcc, html  # noqa: E402

from dashboard import charts as C  # noqa: E402
from src.analysis import kpis as K  # noqa: E402
from src.data.clean import load_processed  # noqa: E402
from src.visualization.style import SURFACE, TEXT_PRIMARY, TEXT_SECONDARY  # noqa: E402

DAY = load_processed("day")
HOUR = load_processed("hour")

FILTERS = {
    "year": ("Year", sorted(DAY["year"].unique().tolist())),
    "season_label": ("Season", [str(s) for s in DAY["season_label"].cat.categories]),
    "day_type": ("Day type", [str(s) for s in DAY["day_type"].cat.categories]),
    "weather_group": ("Weather", [str(s) for s in DAY["weather_group"].cat.categories]),
}
SEGMENT_OPTIONS = [{"label": "Registered", "value": "registered"}, {"label": "Casual", "value": "casual"}]

CARD = {"background": "white", "border": "1px solid #e4e3df", "borderRadius": "8px", "padding": "12px 16px"}
GRAPH_CFG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def dropdown(fid: str, label: str, options: list) -> html.Div:
    return html.Div([
        html.Label(label, style={"fontSize": "12px", "color": TEXT_SECONDARY}),
        dcc.Dropdown(id=f"f-{fid}", options=[{"label": str(o), "value": o} for o in options], value=options,
                     multi=True, clearable=False),
    ], style={"flex": "1", "minWidth": "180px"})


def kpi_tile(tid: str, label: str) -> html.Div:
    return html.Div([
        html.Div(label, style={"fontSize": "12px", "color": TEXT_SECONDARY}),
        html.Div(id=tid, style={"fontSize": "26px", "fontWeight": 600, "color": TEXT_PRIMARY}),
        html.Div(id=f"{tid}-sub", style={"fontSize": "11px", "color": TEXT_SECONDARY}),
    ], style={**CARD, "flex": "1", "minWidth": "150px"})


def graph(gid: str) -> dcc.Graph:
    return dcc.Graph(id=gid, config=GRAPH_CFG, style={**CARD, "padding": "4px"})


def row(*children, cols: int = 2) -> html.Div:
    return html.Div(list(children), style={"display": "grid", "gridTemplateColumns": f"repeat({cols}, 1fr)",
                                           "gap": "12px", "marginBottom": "12px"})


app = Dash(__name__, title="Bike Sharing Demand Dashboard")
app.layout = html.Div([
    html.H2("Bike Sharing Demand & Usage Patterns", style={"margin": "0 0 2px"}),
    html.Div("Capital Bikeshare, Washington D.C., 2011-2012 (UCI Bike Sharing Dataset). "
             "Daily charts use day.csv; hourly charts use hour.csv. The two grains are never mixed.",
             style={"color": TEXT_SECONDARY, "fontSize": "13px", "marginBottom": "12px"}),
    html.Div([dropdown(k, lbl, opts) for k, (lbl, opts) in FILTERS.items()] + [
        html.Div([html.Label("User type", style={"fontSize": "12px", "color": TEXT_SECONDARY}),
                  dcc.Checklist(id="f-segment", options=SEGMENT_OPTIONS, value=["registered", "casual"],
                                inline=True, inputStyle={"marginRight": "4px", "marginLeft": "8px"})],
                 style={"minWidth": "180px"}),
    ], style={**CARD, "display": "flex", "gap": "12px", "flexWrap": "wrap", "marginBottom": "6px"}),
    html.Div("Weather filter: daily charts use each day's dominant weather; hourly charts use each hour's weather.",
             style={"fontSize": "11px", "color": TEXT_SECONDARY, "marginBottom": "12px"}),
    html.Div([kpi_tile(t, l) for t, l in [("k-total", "Total rentals"), ("k-mean", "Mean rentals / day"),
                                          ("k-median", "Median rentals / day"), ("k-share", "Casual share"),
                                          ("k-peak", "Peak hour (mean / hour)")]],
             style={"display": "flex", "gap": "12px", "flexWrap": "wrap", "marginBottom": "12px"}),
    dcc.Tabs(id="tabs", value="overview", children=[
        dcc.Tab(label="Overview", value="overview", children=[
            html.Div(style={"height": "12px"}), graph("g-trend"), html.Div(style={"height": "12px"}), graph("g-monthly")]),
        dcc.Tab(label="Time patterns", value="time", children=[
            html.Div(style={"height": "12px"}), graph("g-hourly"), html.Div(style={"height": "12px"}), graph("g-heatmap")]),
        dcc.Tab(label="Weather", value="weather", children=[
            html.Div(style={"height": "12px"}), row(graph("g-temp"), graph("g-weather")),
            row(graph("g-hum"), graph("g-wind"))]),
        dcc.Tab(label="User segments", value="segments", children=[
            html.Div(style={"height": "12px"}), graph("g-seghour"), html.Div(style={"height": "12px"}),
            row(graph("g-share"), graph("g-weekday"))]),
        dcc.Tab(label="Operations", value="ops", children=[
            html.Div(style={"height": "12px"}), graph("g-tiers"),
            html.Div([html.H4("Busiest and quietest hour slots (mean rentals per hour)", style={"margin": "4px 0"}),
                      html.Div("Implications only: the data has no station inventory, so availability and "
                               "stockouts are not measured.", style={"fontSize": "12px", "color": TEXT_SECONDARY}),
                      dash_table.DataTable(id="t-slots", style_cell={"fontFamily": "inherit", "fontSize": "13px",
                                                                     "padding": "4px 8px", "textAlign": "left"},
                                           style_header={"fontWeight": 600, "background": "#e8f0fb"})],
                     style={**CARD, "marginTop": "12px"})]),
    ]),
    html.Div("Source: Fanaee-T & Gama (2013), UCI Machine Learning Repository. Associations only, not causal effects.",
             style={"fontSize": "11px", "color": TEXT_SECONDARY, "marginTop": "16px"}),
], style={"fontFamily": "Inter, Segoe UI, Helvetica, Arial, sans-serif", "background": SURFACE,
          "padding": "20px 28px", "maxWidth": "1400px", "margin": "0 auto"})


def apply_filters(df: pd.DataFrame, years, seasons, day_types, weather) -> pd.DataFrame:
    return df[df["year"].isin(years) & df["season_label"].astype(str).isin(seasons)
              & df["day_type"].astype(str).isin(day_types) & df["weather_group"].astype(str).isin(weather)]


FILTER_INPUTS = [Input(f"f-{k}", "value") for k in FILTERS] + [Input("f-segment", "value")]


@app.callback(
    [Output(i, "children") for t in ["k-total", "k-mean", "k-median", "k-share", "k-peak"] for i in (t, f"{t}-sub")],
    FILTER_INPUTS)
def update_kpis(years, seasons, day_types, weather, segments):
    d = apply_filters(DAY, years, seasons, day_types, weather)
    h = apply_filters(HOUR, years, seasons, day_types, weather)
    if d.empty:
        return ["-", "no days match"] * 5
    total = d["cnt"].sum()
    prof = h.groupby("hr")["cnt"].mean() if not h.empty else pd.Series(dtype=float)
    peak = f"{int(prof.idxmax())}:00" if len(prof) else "-"
    return [f"{total:,.0f}", f"{len(d)} days selected",
            f"{d['cnt'].mean():,.0f}", "all users",
            f"{d['cnt'].median():,.0f}", "all users",
            f"{d['casual'].sum() / total:.1%}", f"registered {d['registered'].sum() / total:.1%}",
            peak, f"{prof.max():,.0f} rentals / hour" if len(prof) else ""]


@app.callback([Output(g, "figure") for g in ["g-trend", "g-monthly", "g-hourly", "g-heatmap", "g-temp", "g-weather",
                                             "g-hum", "g-wind", "g-seghour", "g-share", "g-weekday", "g-tiers"]]
              + [Output("t-slots", "data"), Output("t-slots", "columns")],
              FILTER_INPUTS)
def update_charts(years, seasons, day_types, weather, segments):
    d = apply_filters(DAY, years, seasons, day_types, weather)
    h = apply_filters(HOUR, years, seasons, day_types, weather)
    segs = segments or ["registered", "casual"]
    # Single-segment views: total when both/none selected, else the chosen segment.
    seg = segs[0] if len(segs) == 1 else "cnt"
    if d.empty or h.empty:
        e = C.empty()
        return [e] * 12 + [[], []]
    figs = [C.daily_trend(d, segs), C.monthly_stacked(d, segs), C.hourly_by_daytype(h, seg),
            C.hour_weekday_heatmap(h, seg), C.temperature_scatter(d, seg), C.weather_bars(d, segs),
            C.env_scatter(d, "hum_pct", "Humidity (%)", seg), C.env_scatter(d, "windspeed_kmh", "Wind speed (km/h)", seg),
            C.segment_hourly(h), C.casual_share_monthly(d), C.weekday_mix(d), C.demand_tiers(h)]
    w = K.demand_windows(h)
    slots = pd.concat([w.nlargest(5, "mean_cnt").assign(rank="Busiest"),
                       w.nsmallest(5, "mean_cnt").assign(rank="Quietest")])
    table = pd.DataFrame({"Group": slots["rank"], "Day type": slots["day_type"].astype(str),
                          "Hour": slots["hr"].map(lambda x: f"{x:02d}:00"),
                          "Mean / h": slots["mean_cnt"].round(0).astype(int),
                          "p10-p90": slots["p10_cnt"].round(0).astype(int).astype(str) + "-"
                          + slots["p90_cnt"].round(0).astype(int).astype(str),
                          "Observed hours": slots["hours"], "Tier": slots["tier"]})
    return figs + [table.to_dict("records"), [{"name": c, "id": c} for c in table.columns]]


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=8050)
