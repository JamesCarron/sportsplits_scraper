"""Layout builder for the Age-Group Analysis section: three tabs (Pro-Ironman,
Ironman, Ireland). Static content, precomputed once at startup by age_group_page.py,
so this just renders it -- no callbacks needed for tab switching (dcc.Tabs handles
that client-side).
"""
from dash import dcc, html

from sportsplits.analytics import AG_ORDER
from sportsplits.viz import fmt_td

_SIGMA_COLS = [(-3, "-3σ"), (-2, "-2σ"), (-1, "-1σ"), (1, "+1σ"), (2, "+2σ"), (3, "+3σ")]
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


def _age_table(summary_df, gender="Male"):
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
        html.Img(src=content["img_ag_full"], className="athlete-chart"),
        _age_table(content["summary_full"]),
        html.H3("Ironman 70.3 World Championship"),
        html.Img(src=content["img_ag_half"], className="athlete-chart"),
        _age_table(content["summary_half"]),
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
        html.Img(src=content["img_ag_full"], className="athlete-chart"),
        _age_table(content["summary_full"]),
        html.H3("Ironman 70.3"),
        html.Img(src=content["img_ag_half"], className="athlete-chart"),
        _age_table(content["summary_half"]),
    ])


def _ireland_distance_tab(d: dict):
    body = [
        html.Div(className="stats-bar", children=[
            _stat(str(d["n_races"]), "Distance/events"),
            _stat(str(d["n_rows"]), "Finisher rows"),
        ]),
    ]
    if d["img_ag"] is None:
        body.append(html.P(
            "No standard 5-year age-group breakdown available for this "
            "distance — either results are scored by team rather than "
            "individual age band (e.g. relay), or the only categories "
            "published aren't standard 5-year bands.", className="ag-note"))
    else:
        body += [
            html.Img(src=d["img_ag"], className="athlete-chart"),
            _age_table(d["summary"]),
        ]
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
        dcc.Tabs(id="age-group-tabs", value="pro-ironman", children=[
            dcc.Tab(label="Pro-Ironman", value="pro-ironman", children=[pro_ironman_tab(pro_content)]),
            dcc.Tab(label="Ironman", value="ironman", children=[ironman_regular_tab(regular_content)]),
            dcc.Tab(label="Ireland", value="ireland", children=[ireland_tab(ireland_content)]),
        ]),
    ])
