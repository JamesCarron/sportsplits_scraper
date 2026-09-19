"""Precomputes the Age-Group Analysis page's content once at app startup (mirrors
races.py's load_all() -- static, non-interactive analysis, so it's computed once and
served from memory rather than recomputed per-request).
"""
from sportsplits.analytics import age_group_summary, slowest_pro_female, classify_distance, WC_RACE_DATES

# Only these distance/format buckets are shown on the Ireland tab -- Duathlon,
# Aquabike, Relay, Mixed, and Other/Unspecified are gathered (see below) but
# not displayed: too few races, a different discipline, or not comparable on
# an age-group finish-time chart at all.
_IRELAND_DISTANCES = ["Try-a-Tri", "Super Sprint", "Sprint", "Olympic / Standard", "Middle / Half"]
from sportsplits.viz.age_groups import plot_age_groups, plot_slowest_female
from sportsplits.viz.web import fig_to_base64
from sportsplits.parsers.ironman.events import EVENTS as WC_EVENTS
from sportsplits.parsers.ironman.regular_events import load_regular_races
from sportsplits.parsers.ironman.regular_races_manifest import FULL_RACES, HALF_RACES
from sportsplits.parsers.raceresult.common import load_processed_csv


def _load_wc(distance: str) -> list:
    return [(spec.name, load_processed_csv(spec.processed_path)) for spec in WC_EVENTS if spec.distance == distance]


def _both_modes(summary, title) -> dict:
    """Both display-mode images for one chart, for the page's std-dev/percentile
    toggle -- both are rendered up front (not on demand) since this whole page
    is precomputed once at startup and served statically, no callback involved."""
    fig_sigma = plot_age_groups(summary, title, mode="sigma")
    fig_pct = plot_age_groups(summary, title, mode="percentile")
    return {
        "sigma": fig_to_base64(fig_sigma) if fig_sigma is not None else None,
        "percentile": fig_to_base64(fig_pct) if fig_pct is not None else None,
    }


def build_pro_ironman_content() -> dict:
    """Ironman World Championship: slowest-pro-female + age-group competitiveness."""
    wc_full = _load_wc("full")
    wc_half = _load_wc("70.3")

    result_half, avg_raw_half, avg_clean_half = slowest_pro_female(wc_half, WC_RACE_DATES)
    result_full, avg_raw_full, avg_clean_full = slowest_pro_female(wc_full, WC_RACE_DATES)
    summary_full = age_group_summary(wc_full)
    summary_half = age_group_summary(wc_half)

    return {
        "slowest_half": (result_half, avg_raw_half, avg_clean_half),
        "slowest_full": (result_full, avg_raw_full, avg_clean_full),
        "img_slowest_half": fig_to_base64(plot_slowest_female(
            result_half, avg_clean_half, "IM 70.3 WC ",
            "Slowest pro female finisher — Ironman 70.3 World Championship")),
        "img_slowest_full": fig_to_base64(plot_slowest_female(
            result_full, avg_clean_full, "IM WC ",
            "Slowest pro female finisher — Ironman World Championship (full)")),
        "img_ag_full": _both_modes(
            summary_full, "Full-distance Ironman World Championship — age-group participants & median time"),
        "img_ag_half": _both_modes(
            summary_half, "Ironman 70.3 World Championship — age-group participants & median time"),
        "summary_full": summary_full,
        "summary_half": summary_half,
    }


def build_ironman_regular_content() -> dict:
    """Regular (non-championship) Ironman races, 2025-2026: age-group competitiveness."""
    reg_full = load_regular_races(FULL_RACES)
    reg_half = load_regular_races(HALF_RACES)

    summary_full = age_group_summary(reg_full)
    summary_half = age_group_summary(reg_half)

    return {
        "n_full": len(FULL_RACES),
        "n_half": len(HALF_RACES),
        "img_ag_full": _both_modes(
            summary_full, "Regular full-distance Ironman races 2025-2026 — age-group participants & median time"),
        "img_ag_half": _both_modes(
            summary_half, "Regular Ironman 70.3 races 2025-2026 — age-group participants & median time"),
        "summary_full": summary_full,
        "summary_half": summary_half,
    }


def build_ireland_content() -> dict:
    """Irish triathlons, 2024-2026. Gathered in two passes: an initial pass
    (Monster Timing + Sportsplits.com), then a "full systematic sweep" against
    Triathlon Ireland's official race calendar to track down every other
    reachable timing provider for the ~150+ events that pass had missed --
    surfaced several more small/one-off RaceResult accounts plus additional
    Sportsplits.com races. Split into sub-tabs by distance/format (Sprint,
    Olympic, Middle/Half, ...) -- see analytics.classify_distance() for how
    each race/event name is bucketed, since results across distances aren't
    comparable on the same age-group finish-time chart.
    """
    from sportsplits.parsers.raceresult.monster_timing_manifest import RACES as MT_RACES
    from sportsplits.parsers.raceresult.kerry_galway_manifest import RACES as KG_RACES
    from sportsplits.parsers.raceresult.justruns_manifest import RACES as JR_RACES
    from sportsplits.parsers.raceresult.small_races_manifest import RACES as SM_RACES
    from sportsplits.parsers.raceresult.leinster_races import RACES as LN_RR_RACES
    from sportsplits.parsers.sportsplits.manifest import RACES as SS_RACES
    from sportsplits.parsers.sportsplits.manifest_leinster import RACES as SS_LN_RACES
    from sportsplits.parsers.sportsplits.common import load_race as load_sportsplits_race

    races = [(r.name, load_processed_csv(r.processed_path), "monster_timing") for r in MT_RACES]
    other_rr = list(KG_RACES) + list(JR_RACES) + list(SM_RACES) + list(LN_RR_RACES)
    races += [(r.name, load_processed_csv(r.processed_path), "raceresult_other") for r in other_rr]

    for slug, name, year in list(SS_RACES) + list(SS_LN_RACES):
        for _, (event_name, df) in load_sportsplits_race(slug).items():
            races.append((f"{name} {year} - {event_name}", df, "sportsplits"))

    # Only the distance buckets in _IRELAND_DISTANCES are shown -- see its
    # docstring for why the rest are gathered but not displayed.
    by_distance: dict[str, list] = {}
    for name, df, source in races:
        label = classify_distance(name)
        if label in _IRELAND_DISTANCES:
            by_distance.setdefault(label, []).append((name, df, source))

    distances = []
    for label in _IRELAND_DISTANCES:
        bucket = by_distance.get(label)
        if not bucket:
            continue
        summary = age_group_summary([(name, df) for name, df, _ in bucket])
        # _both_modes()/plot_age_groups() return None for a mode when nothing
        # survives its standard-band filtering for either gender -- not
        # expected for these 5 buckets given today's data, but kept defensive
        # in case a future pull adds a race whose only bands are non-standard
        # widths.
        title = f"Irish Triathlons 2024-2026 — {label} — age-group participants & median time"
        distances.append({
            "label": label,
            "n_races": len(bucket),
            "n_rows": sum(len(df) for _, df, _ in bucket),
            "img_ag": {"sigma": None, "percentile": None} if summary.empty else _both_modes(summary, title),
            "summary": summary,
        })

    shown = [row for bucket in by_distance.values() for row in bucket]
    return {
        "n_monster_timing": sum(1 for _, _, source in shown if source == "monster_timing"),
        "n_raceresult_other": sum(1 for _, _, source in shown if source == "raceresult_other"),
        "n_sportsplits": sum(1 for _, _, source in shown if source == "sportsplits"),
        "n_events": len(shown),
        "n_rows": sum(len(df) for _, df, _ in shown),
        "distances": distances,
    }
