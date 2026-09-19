"""Charts for the Age-Group Analysis page: age-group participant/median-time bands,
either as 1/2/3-sigma lines (assumes a normal distribution) or as an empirical
percentile ladder (reads the real, possibly skewed, distribution directly) -- see
plot_age_groups()'s `mode` argument -- plus the slowest-pro-female-excluding-
outliers scatter.

Plotly, not matplotlib: these figures ship as a JSON spec to dcc.Graph and
render client-side -- no server-side rasterization, which matters a lot for
the per-race Age-Group Breakdown (callbacks.py), computed live per
race-selector change rather than once at startup like everything else that
calls plot_age_groups(). Measured matplotlib equivalent: ~1.5s per figure
(bbox_inches='tight' + 150 dpi PNG encoding) x2 for both display modes,
enough to make every race selection feel broken. See docs/REFACTOR_NOTES.md.
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from sportsplits.analytics import AG_ORDER, PERCENTILE_LADDER

# (alpha, dash) -- alpha fades toward the widest/least-exclusive band, dash
# style distinguishes them when overlapping lines are close together. Matches
# the matplotlib version's ":"/"--"/"-."/"-"  mapping 1:1 (dot/dash/dashdot/solid).
_SIGMA_LINES = [(3, "99.7%", 0.45, "dot"), (2, "95%", 0.6, "dash"), (1, "68%", 0.8, "dashdot")]
_PERCENTILE_LINES = {60: (0.35, "dot"), 40: (0.45, "dash"), 30: (0.55, "dash"),
                      20: (0.65, "dashdot"), 10: (0.75, "dashdot"), 5: (0.85, "solid"), 2: (1.0, "solid")}
_GENDER_COLORS = {"Male": "#3b6ea5", "Female": "#a5473b"}


def _hours(td) -> float:
    return td.total_seconds() / 3600


def _prep(summary: pd.DataFrame, max_band: str) -> dict:
    under_cutoff = AG_ORDER[:AG_ORDER.index(max_band) + 1]
    subs = {}
    for gender in ["Male", "Female"]:
        sub = summary[summary["Gender"] == gender].copy()
        sub = sub[sub["Band"].isin(under_cutoff)].copy()
        sub["order"] = sub["Band"].map(under_cutoff.index)
        sub = sub.sort_values("order")
        subs[gender] = sub
    return subs


def plot_age_groups(summary: pd.DataFrame, title: str, highlight=("25-29", "30-34"),
                     max_band="55-59", mode="sigma"):
    """summary: output of analytics.age_group_summary(). Male/Female panels share
    y-axes (bars = participants, line = median finish time with a spread band).

    mode="sigma" (default): median +/- 1/2/3 standard deviations, labeled by
    their normal-distribution coverage (68%/95%/99.7% of finishers) -- assumes
    the data is normally distributed around the median.

    mode="percentile": an empirical ladder (Top 60%, Median, Top 40%, 30%, 20%,
    10%, 5%, 2% -- see analytics.PERCENTILE_LADDER) read directly off the real
    distribution, so a skewed field (e.g. a long slow-finisher tail) shows up
    as a visibly asymmetric spread around the median instead of being averaged
    away into a symmetric band.

    Returns None if nothing survives the standard-band/max_band filtering for
    either gender (e.g. a bucket whose only bands are non-standard widths like
    "20-34", or has no individual Male/Female rows at all) -- there's nothing
    chartable in that case, and the caller is expected to handle None."""
    subs = _prep(summary, max_band)
    if all(sub.empty for sub in subs.values()):
        return None

    if mode == "sigma":
        for sub in subs.values():
            sub["median_h"] = sub["median"].map(_hours)
            sub["std_h"] = sub["std"].map(_hours)
        lo = min((subs[g]["median_h"] - 3 * subs[g]["std_h"]).min() for g in subs if not subs[g].empty)
        hi = max((subs[g]["median_h"] + 3 * subs[g]["std_h"]).max() for g in subs if not subs[g].empty)
    else:
        for sub in subs.values():
            sub["median_h"] = sub["median"].map(_hours)
            for p in PERCENTILE_LADDER:
                sub[f"p{p}_h"] = sub[f"p{p}"].map(_hours)
        lo = min(subs[g][f"p{min(PERCENTILE_LADDER)}_h"].min() for g in subs if not subs[g].empty)
        hi = max(subs[g][f"p{max(PERCENTILE_LADDER)}_h"].max() for g in subs if not subs[g].empty)
    pad = (hi - lo) * 0.05
    ylim = [lo - pad, hi + pad]

    fig = make_subplots(rows=1, cols=2, subplot_titles=["Male", "Female"],
                         specs=[[{"secondary_y": True}, {"secondary_y": True}]])

    for col, gender in enumerate(["Male", "Female"], start=1):
        sub = subs[gender]
        color = _GENDER_COLORS[gender]
        bar_colors = ["#f2a516" if b in highlight else color for b in sub["Band"]]
        first_panel = col == 1

        fig.add_trace(go.Bar(
            x=sub["Band"], y=sub["n"], marker_color=bar_colors, opacity=0.75,
            name="Participants", showlegend=False,
            hovertemplate="%{x}: %{y} participants<extra></extra>",
        ), row=1, col=col, secondary_y=False)

        fig.add_trace(go.Scatter(
            x=sub["Band"], y=sub["median_h"], mode="lines+markers",
            line=dict(color="black", width=2), marker=dict(size=7),
            name="Median", showlegend=first_panel, legendgroup="median",
            hovertemplate="%{x}: %{y:.2f}h<extra>Median</extra>",
        ), row=1, col=col, secondary_y=True)

        if mode == "sigma":
            for sigma, pct, alpha, dash in _SIGMA_LINES:
                line = dict(color=f"rgba(0,0,0,{alpha})", width=1.5, dash=dash)
                fig.add_trace(go.Scatter(
                    x=sub["Band"], y=sub["median_h"] + sigma * sub["std_h"], mode="lines",
                    line=line, name=f"±{pct} of finishers", legendgroup=f"s{sigma}",
                    showlegend=first_panel, hoverinfo="skip",
                ), row=1, col=col, secondary_y=True)
                fig.add_trace(go.Scatter(
                    x=sub["Band"], y=sub["median_h"] - sigma * sub["std_h"], mode="lines",
                    line=line, name=f"±{pct} of finishers", legendgroup=f"s{sigma}",
                    showlegend=False, hoverinfo="skip",
                ), row=1, col=col, secondary_y=True)
            y_title = "Median finish (hours)"
        else:
            for p in PERCENTILE_LADDER:
                alpha, dash = _PERCENTILE_LINES[p]
                fig.add_trace(go.Scatter(
                    x=sub["Band"], y=sub[f"p{p}_h"], mode="lines",
                    line=dict(color=f"rgba(0,0,0,{alpha})", width=1.5, dash=dash),
                    name=f"Top {p}%", legendgroup=f"p{p}", showlegend=first_panel,
                    hovertemplate=f"%{{x}}: %{{y:.2f}}h<extra>Top {p}%</extra>",
                ), row=1, col=col, secondary_y=True)
            y_title = "Finish time (hours)"

        fig.update_yaxes(title_text="Participants", secondary_y=False, row=1, col=col)
        fig.update_yaxes(title_text=y_title, range=ylim, secondary_y=True, row=1, col=col)
        fig.update_xaxes(title_text="Age group", tickangle=45, row=1, col=col)

    fig.update_layout(
        title=title, height=520, barmode="group",
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5, font=dict(size=10)),
        margin=dict(b=120),
    )
    return fig


def plot_slowest_female(result: pd.DataFrame, avg_clean, prefix: str, title: str):
    """result: output of analytics.slowest_pro_female()."""
    result = result.copy()
    result["short"] = result["race"].str.replace(prefix, "", regex=False)
    if "date" in result.columns:
        result = result.sort_values("date")

    x = list(range(len(result)))
    raw_h = result["raw_slowest"].map(_hours)
    clean_h = result["clean_slowest"].map(_hours)

    fig = go.Figure()
    for xi, r, c in zip(x, raw_h, clean_h):
        if r != c:
            fig.add_trace(go.Scatter(x=[xi, xi], y=[c, r], mode="lines",
                                      line=dict(color="#cccccc", width=1),
                                      showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=raw_h, mode="markers", marker=dict(color="#c9506b", size=11),
                              name="Raw slowest", text=result["short"],
                              hovertemplate="%{text}: %{y:.2f}h<extra>Raw slowest</extra>"))
    fig.add_trace(go.Scatter(x=x, y=clean_h, mode="markers", marker=dict(color="#2f6f5e", size=11),
                              name="Outliers excluded", text=result["short"],
                              hovertemplate="%{text}: %{y:.2f}h<extra>Outliers excluded</extra>"))
    fig.add_hline(y=_hours(avg_clean), line_dash="dash", line_color="#2f6f5e",
                  annotation_text=f"Average (excl. outliers): {avg_clean}", annotation_position="top left")

    fig.update_xaxes(tickmode="array", tickvals=x, ticktext=result["short"].tolist(), tickangle=-40)
    fig.update_yaxes(title_text="Finish time (hours)")
    fig.update_layout(title=f"{title} (chronological)", height=480,
                       legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig
