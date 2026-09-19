"""Charts for the Age-Group Analysis page: age-group participant/median-time bands,
either as 1/2/3-sigma lines (assumes a normal distribution) or as an empirical
percentile ladder (reads the real, possibly skewed, distribution directly) -- see
plot_age_groups()'s `mode` argument -- plus the slowest-pro-female-excluding-
outliers scatter."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from sportsplits.analytics import AG_ORDER, PERCENTILE_LADDER

_SIGMA_LINES = [(3, "99.7%", 0.45, ":"), (2, "95%", 0.6, "--"), (1, "68%", 0.8, "-.")]

# Darkest/thickest for the most exclusive (fastest) thresholds, fading out
# toward the least exclusive (Top 60%) -- reads like an achievement ladder,
# so the elite end is the one worth visually emphasizing. Ordered slowest to
# fastest to match PERCENTILE_LADDER.
_PERCENTILE_LINES = {60: (0.35, ":"), 40: (0.45, "--"), 30: (0.55, "--"),
                      20: (0.65, "-."), 10: (0.75, "-."), 5: (0.85, "-"), 2: (1.0, "-")}


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
    ylim = (lo - pad, hi + pad)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    legend_handles = legend_labels = None
    for ax, gender, color in zip(axes, ["Male", "Female"], ["#3b6ea5", "#a5473b"]):
        sub = subs[gender]
        bar_colors = ["#f2a516" if b in highlight else color for b in sub["Band"]]
        ax.bar(sub["Band"], sub["n"], color=bar_colors, alpha=0.75)
        ax.set_ylabel("Participants")
        ax.set_xlabel("Age group")
        ax.tick_params(axis="x", rotation=45)
        ax.set_title(gender)

        ax2 = ax.twinx()
        x = sub["Band"]
        ax2.plot(x, sub["median_h"], color="black", marker="o", linewidth=2, zorder=3, label="Median")
        if mode == "sigma":
            for sigma, pct, alpha, ls in _SIGMA_LINES:
                ax2.plot(x, sub["median_h"] + sigma * sub["std_h"], color="black", alpha=alpha,
                         linewidth=1.1, linestyle=ls, zorder=2, label=f"±{pct} of finishers")
                ax2.plot(x, sub["median_h"] - sigma * sub["std_h"], color="black", alpha=alpha,
                         linewidth=1.1, linestyle=ls, zorder=2)
            ax2.set_ylabel("Median finish (hours)")
        else:
            for p in PERCENTILE_LADDER:
                alpha, ls = _PERCENTILE_LINES[p]
                ax2.plot(x, sub[f"p{p}_h"], color="black", alpha=alpha, linewidth=1.3,
                         linestyle=ls, zorder=2, label=f"Top {p}%")
            ax2.set_ylabel("Finish time (hours)")
        ax2.set_ylim(*ylim)
        if legend_handles is None:
            legend_handles, legend_labels = ax2.get_legend_handles_labels()

    fig.suptitle(title)
    ncol = 4 if mode == "sigma" else 8
    fig.legend(legend_handles, legend_labels, loc="lower center", ncol=ncol,
               bbox_to_anchor=(0.5, -0.04), frameon=False, fontsize=9 if mode == "sigma" else 8)
    fig.tight_layout()
    return fig


def plot_slowest_female(result: pd.DataFrame, avg_clean, prefix: str, title: str):
    """result: output of analytics.slowest_pro_female()."""
    result = result.copy()
    result["short"] = result["race"].str.replace(prefix, "", regex=False)
    if "date" in result.columns:
        result = result.sort_values("date")

    fig, ax = plt.subplots(figsize=(9, 5))
    x = range(len(result))
    ax.scatter(x, result["raw_slowest"].map(_hours), label="Raw slowest", color="#c9506b", s=70, zorder=3)
    ax.scatter(x, result["clean_slowest"].map(_hours), label="Outliers excluded", color="#2f6f5e", s=70, zorder=3)
    for xi, raw_h, clean_h in zip(x, result["raw_slowest"].map(_hours), result["clean_slowest"].map(_hours)):
        if raw_h != clean_h:
            ax.plot([xi, xi], [clean_h, raw_h], color="#ccc", linewidth=1, zorder=1)
    ax.axhline(_hours(avg_clean), color="#2f6f5e", linestyle="--", linewidth=1,
               label=f"Average (excl. outliers): {avg_clean}")
    ax.set_xticks(list(x))
    ax.set_xticklabels(result["short"], rotation=40, ha="right", fontsize=8)
    ax.set_ylabel("Finish time (hours)")
    ax.set_title(f"{title} (chronological)")
    ax.legend(fontsize=8)
    ax.grid(axis="y", color="#eee")
    fig.tight_layout()
    return fig
