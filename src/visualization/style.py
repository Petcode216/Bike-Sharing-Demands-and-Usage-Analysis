"""Shared visual style for static (matplotlib) and interactive (plotly) charts.

Colors follow a validated categorical order (blue, orange, aqua, ...). Identity is
fixed per entity, never per rank: registered is always blue, casual always orange.
"""
import matplotlib as mpl
import matplotlib.pyplot as plt

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"

CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
NEUTRAL = "#8a8984"

# Fixed entity -> color mapping, shared by figures and the dashboard.
SEGMENT_COLORS: dict[str, str] = {"registered": CATEGORICAL[0], "casual": CATEGORICAL[1],
                                  "cnt": TEXT_PRIMARY}
SEGMENT_NAMES: dict[str, str] = {"registered": "Registered", "casual": "Casual", "cnt": "Total"}
DAY_TYPE_COLORS: dict[str, str] = {"Working day": CATEGORICAL[0], "Weekend": CATEGORICAL[1],
                                   "Holiday": CATEGORICAL[2]}
YEAR_COLORS: dict[int, str] = {2011: CATEGORICAL[2], 2012: CATEGORICAL[0]}
WEATHER_COLORS: dict[str, str] = {"Clear / partly cloudy": CATEGORICAL[0], "Mist / cloudy": CATEGORICAL[1],
                                  "Rain / snow": CATEGORICAL[2]}


def apply_matplotlib_style() -> None:
    """Recessive axes and grid, thin marks, readable type."""
    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "figure.dpi": 110, "savefig.dpi": 150, "savefig.bbox": "tight",
        "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "semibold", "axes.titlelocation": "left",
        "axes.labelsize": 10, "axes.labelcolor": TEXT_SECONDARY, "axes.edgecolor": GRID,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "axes.axisbelow": True,
        "grid.color": GRID, "grid.linewidth": 0.6, "xtick.color": TEXT_SECONDARY, "ytick.color": TEXT_SECONDARY,
        "text.color": TEXT_PRIMARY, "lines.linewidth": 2.0, "lines.markersize": 5,
        "legend.frameon": False, "legend.fontsize": 9, "axes.prop_cycle": mpl.cycler(color=CATEGORICAL),
    })


def thousands(x: float, _pos: int | None = None) -> str:
    return f"{x/1000:.0f}k" if abs(x) >= 1000 else f"{x:.0f}"


def finish(fig: plt.Figure, subtitle: str | None = None) -> plt.Figure:
    """Add a muted source/grain note under the plot."""
    if subtitle:
        import textwrap
        width_chars = int(fig.get_figwidth() * 15)
        # Offset in inches below the axes area so it clears tick and axis labels.
        y = -0.42 / fig.get_figheight()
        fig.text(0.01, y, textwrap.fill(subtitle, width_chars), fontsize=8, color=TEXT_SECONDARY,
                 ha="left", va="top")
    return fig


PLOTLY_LAYOUT: dict = {
    "paper_bgcolor": SURFACE, "plot_bgcolor": SURFACE,
    "font": {"family": "Inter, Segoe UI, Helvetica, Arial, sans-serif", "color": TEXT_PRIMARY, "size": 12},
    "colorway": CATEGORICAL, "hovermode": "closest",
    "margin": {"l": 56, "r": 16, "t": 48, "b": 44},
    "xaxis": {"gridcolor": GRID, "linecolor": GRID, "zeroline": False},
    "yaxis": {"gridcolor": GRID, "linecolor": GRID, "zeroline": False},
    "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
    "hoverlabel": {"bgcolor": "white", "font": {"color": TEXT_PRIMARY}},
}
