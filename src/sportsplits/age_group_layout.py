"""Layout builder for the Age-Group Analysis section: three tabs (Pro-Ironman,
Ironman, Ireland). Static content, precomputed once at startup by age_group_page.py,
so this just renders it -- no callbacks needed for tab switching (dcc.Tabs handles
that client-side). The one exception is the std-dev/percentile display toggle,
which is a genuine client-side callback (see callbacks.py's
register_stats_mode_toggle()) purely to flip a CSS class -- everything both
modes could ever show is already rendered into the page up front by
age_group_page.py, nothing is computed on click.
"""
from dash import dcc, html

from sportsplits.analytics import AG_ORDER, PERCENTILE_LADDER
from sportsplits.viz import fmt_td

_SIGMA_COLS = [(-3, "-3σ"), (-2, "-2σ"), (-1, "-1σ"), (1, "+1σ"), (2, "+2σ"), (3, "+3σ")]
# Table column order matches the chart's line order: slowest/least-exclusive
# first, median in the middle, fastest/most-exclusive last.
_PERCENTILE_COLS_BEFORE_MEDIAN = [p for p in PERCENTILE_LADDER if p > 50]
_PERCENTILE_COLS_AFTER_MEDIAN = [p for p in PERCENTILE_LADDER if p < 50]
_HIGHLIGHT = ("25-29", "30-34")

# Same cutoff plot_age_groups() charts use (its own default max_band="55-59")
# -- the table should show exactly the bands the chart above it shows, not
# more: drops 60+ bands and any non-standard-width band (e.g. Monster
# Timing's "20-34"/"50+") that isn't a genuine 5-year band in AG_ORDER at all.
_TABLE_BANDS = set(AG_ORDER[:AG_ORDER.index("55-59") + 1])


def _fmt_bound(td):
    """Like fmt_td, but a negative bound (small/noisy groups where median-N*std
    dips below zero) is displayed as '—' -- a negative finish time isn't a
    real value, just an artifact of a symmetric sigma band on a skewed sample."""
    if td is not None and td.total_seconds() < 0:
        return "—"
    return fmt_td(td)


def _age_table_sigma(summary_df, gender="Male"):
    df = summary_df[summary_df["Gender"] == gender]
    df = df[df["Band"].isin(_TABLE_BANDS)].set_index("Band")
    header = html.Tr([html.Th("Age group"), html.Th("Participants"),
                       *[html.Th(lbl) for _, lbl in _SIGMA_COLS[:3]],
                       html.Th("Median"),
                       *[html.Th(lbl) for _, lbl in _SIGMA_COLS[3:]]])
    rows = [header]
    for band in df.index:
        median, std = df.loc[band, "median"], df.loc[band, "std"]
        cells = [html.Td(f"{gender[0]}{band}"), html.Td(int(df.loc[band, "n"]))]
        cells += [html.Td(_fmt_bound(median + sigma * std)) for sigma, _ in _SIGMA_COLS[:3]]
        cells.append(html.Td(html.B(fmt_td(median))))
        cells += [html.Td(_fmt_bound(median + sigma * std)) for sigma, _ in _SIGMA_COLS[3:]]
        rows.append(html.Tr(cells, className="highlight" if band in _HIGHLIGHT else ""))
    return html.Table(rows, className="summary-table ag-table")


def _age_table_percentile(summary_df, gender="Male"):
    df = summary_df[summary_df["Gender"] == gender]
    df = df[df["Band"].isin(_TABLE_BANDS)].set_index("Band")
    header = html.Tr([html.Th("Age group"), html.Th("Participants"),
                       *[html.Th(f"Top {p}%") for p in _PERCENTILE_COLS_BEFORE_MEDIAN],
                       html.Th("Median"),
                       *[html.Th(f"Top {p}%") for p in _PERCENTILE_COLS_AFTER_MEDIAN]])
    rows = [header]
    for band in df.index:
        cells = [html.Td(f"{gender[0]}{band}"), html.Td(int(df.loc[band, "n"]))]
        cells += [html.Td(fmt_td(df.loc[band, f"p{p}"])) for p in _PERCENTILE_COLS_BEFORE_MEDIAN]
        cells.append(html.Td(html.B(fmt_td(df.loc[band, "median"]))))
        cells += [html.Td(fmt_td(df.loc[band, f"p{p}"])) for p in _PERCENTILE_COLS_AFTER_MEDIAN]
        rows.append(html.Tr(cells, className="highlight" if band in _HIGHLIGHT else ""))
    return html.Table(rows, className="summary-table ag-table")


def _chart_and_table(img_dict, summary_df, gender="Male"):
    """One chart+table pair, rendered in both display modes -- CSS (see
    assets/style.css) shows only one at a time based on a class toggled on
    <body> by the page's std-dev/percentile button."""
    return html.Div([
        html.Div(className="stats-sigma", children=[
            html.Img(src=img_dict["sigma"], className="athlete-chart"),
            _age_table_sigma(summary_df, gender),
        ]),
        html.Div(className="stats-percentile", children=[
            html.Img(src=img_dict["percentile"], className="athlete-chart"),
            _age_table_percentile(summary_df, gender),
        ]),
    ])


def stats_mode_toggle():
    """One button, page-wide: flips every _chart_and_table() pair between
    std-dev and percentile mode at once via a class on <body> (clientside
    callback in callbacks.py -- no server round-trip, nothing recomputed)."""
    return html.Button("Showing: Std deviation — click for Percentile",
                        id="stats-mode-toggle", className="stats-mode-btn")


def _stat(value: str, label: str):
    return html.Div(className="stat", children=[html.B(value), " ", label])


def _slowest_female_block(title, result, avg_raw, avg_clean, img):
    if result.empty:
        return html.Div([html.H4(title), html.P("No professional women's field found.", className="ag-note")])
    n_pros = int(result["n_pros"].sum())
    n_excl = int(result["n_excluded_outliers"].sum())
    return html.Div([
        html.H4(title),
        html.Div(className="stats-bar", children=[
            _stat(fmt_td(avg_raw), "Average slowest (raw, incl. outliers)"),
            _stat(fmt_td(avg_clean), "Average slowest (outliers excluded)"),
            _stat(f"{n_excl} / {n_pros}", f"Finishers excluded as outliers ({n_excl / n_pros * 100:.1f}%)"),
        ]),
        html.Img(src=img, className="athlete-chart"),
    ])


def pro_ironman_tab(content: dict):
    slow_half = content["slowest_half"]
    slow_full = content["slowest_full"]
    return html.Div(className="section", children=[
        html.H2("1. Slowest professional female Ironman finisher, excluding outliers"),
        html.P("Restricted to the professional women's field (Age_Group = FPRO). Finish times "
               "above Q3 + 1.5×IQR within each race's pro field are treated as “had an "
               "issue” (mechanical failure, injury, etc.) and excluded before finding the "
               "slowest legitimate finisher.", className="ag-note"),
        _slowest_female_block("Ironman 70.3 World Championship", *slow_half, content["img_slowest_half"]),
        _slowest_female_block("Ironman World Championship (full distance)", *slow_full, content["img_slowest_full"]),

        html.H2("2. Age-group competitiveness"),
        html.P("Bars = participant count. Line = median finish time, with ±1/2/3σ bands "
               "(shown as ±68%/95%/99.7% of finishers). Your transition (25–29 → "
               "30–34) is highlighted.", className="ag-note"),
        html.H3("Full-distance World Championship (Kona / Nice)"),
        _chart_and_table(content["img_ag_full"], content["summary_full"]),
        html.H3("Ironman 70.3 World Championship"),
        _chart_and_table(content["img_ag_half"], content["summary_half"]),
    ])


def ironman_regular_tab(content: dict):
    return html.Div(className="section", children=[
        html.H2("Age-group competitiveness — regular races"),
        html.P(f"Every non-World-Championship Ironman race held 2025-01-01 through "
               f"2026-09-16: {content['n_full']} full-distance races and {content['n_half']} "
               f"70.3 races, {content['n_full'] + content['n_half']} total. This dataset is far "
               f"larger than the World Championship one (elite qualifiers only) — the shape "
               f"here reflects the general age-group population.", className="ag-note"),
        html.H3("Full distance"),
        _chart_and_table(content["img_ag_full"], content["summary_full"]),
        html.H3("Ironman 70.3"),
        _chart_and_table(content["img_ag_half"], content["summary_half"]),
    ])


def _ireland_distance_tab(d: dict):
    body = [
        html.Div(className="stats-bar", children=[
            _stat(str(d["n_races"]), "Distance/events"),
            _stat(str(d["n_rows"]), "Finisher rows"),
        ]),
    ]
    if d["img_ag"]["sigma"] is None:
        body.append(html.P(
            "No standard 5-year age-group breakdown available for this "
            "distance — either results are scored by team rather than "
            "individual age band (e.g. relay), or the only categories "
            "published aren't standard 5-year bands.", className="ag-note"))
    else:
        body.append(_chart_and_table(d["img_ag"], d["summary"]))
    return html.Div(className="section", children=body)


def ireland_tab(content: dict):
    return html.Div(className="section", children=[
        html.H2("Irish Triathlons — 2024 / 2025 / 2026"),
        html.P("Gathered in two passes. First, Monster Timing and Sportsplits.com. Then a "
               "full systematic sweep against Triathlon Ireland's official race calendar, "
               "checking every other event on it for a reachable results host — turning up "
               "a further ~25 small/one-off RaceResult accounts (mostly local club "
               "triathlons/duathlons, found via RaceResult's own public event directory) "
               "plus several more Sportsplits.com races, including Dublin City Triathlon. "
               "Split into sub-tabs below by distance/format, since finish times aren't "
               "comparable across distances — a race whose results list combines multiple "
               "distances in one table (so they can't be separated after the fact) lands in "
               "\"Mixed\"; one with no distance identifiable from its name lands in "
               "\"Other / Unspecified\".", className="ag-note"),
        html.P("Sources checked and deliberately left out: RedTag Timing (no 2024-2026 "
               "triathlon coverage), Timing Solutions Ireland (no triathlons in the window), "
               "and SportsTiming.ie / sportmaniacs.com, Blackwater, Ballyhass and "
               "Carrick-on-Suir (all resolve to sportmaniacs.com, whose robots.txt "
               "disallows automated access to results for all crawlers — not just AI ones — "
               "a general anti-scraping policy, not the AI-specific blocks that justify "
               "browser-based access elsewhere in this app). A number of smaller club races "
               "on the calendar publish no results online at all, or PDF-only.",
               className="ag-note"),
        html.Div(className="stats-bar", children=[
            _stat(str(content["n_monster_timing"]), "Races from Monster Timing"),
            _stat(str(content["n_raceresult_other"]), "Races from other RaceResult accounts"),
            _stat(str(content["n_sportsplits"]), "Races from Sportsplits"),
            _stat(str(content["n_events"]), "Total distance/events"),
            _stat(str(content["n_rows"]), "Total finisher rows"),
        ]),
        dcc.Tabs(id="ireland-distance-tabs", value=content["distances"][0]["label"], children=[
            dcc.Tab(label=f"{d['label']} ({d['n_races']})", value=d["label"],
                    children=[_ireland_distance_tab(d)])
            for d in content["distances"]
        ]),
    ])


def make_age_group_section(pro_content: dict, regular_content: dict, ireland_content: dict):
    return html.Section(className="section", children=[
        html.H2("Age-Group Analysis"),
        html.P("Every age-group chart and table below has two views: median "
               "± std-dev bands (assumes a normal distribution) or an "
               "empirical percentile ladder (reads the real, possibly skewed, "
               "distribution directly). One button switches all of them at "
               "once.", className="ag-note"),
        stats_mode_toggle(),
        dcc.Tabs(id="age-group-tabs", value="pro-ironman", children=[
            dcc.Tab(label="Pro-Ironman", value="pro-ironman", children=[pro_ironman_tab(pro_content)]),
            dcc.Tab(label="Ironman", value="ironman", children=[ironman_regular_tab(regular_content)]),
            dcc.Tab(label="Ireland", value="ireland", children=[ireland_tab(ireland_content)]),
        ]),
    ])
