"""Precomputes the Age-Group Analysis page's content once at app startup (mirrors
races.py's load_all() -- static, non-interactive analysis, so it's computed once and
served from memory rather than recomputed per-request).
"""
from sportsplits.analytics import age_group_summary, slowest_pro_female, WC_RACE_DATES
from sportsplits.viz.age_groups import plot_age_groups, plot_slowest_female
from sportsplits.viz.web import fig_to_base64
from sportsplits.parsers.ironman.events import EVENTS as WC_EVENTS
from sportsplits.parsers.ironman.regular_events import load_regular_races
from sportsplits.parsers.ironman.regular_races_manifest import FULL_RACES, HALF_RACES
from sportsplits.parsers.raceresult.common import load_processed_csv


def _load_wc(distance: str) -> list:
    return [(spec.name, load_processed_csv(spec.processed_path)) for spec in WC_EVENTS if spec.distance == distance]


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
        "img_ag_full": fig_to_base64(plot_age_groups(
            summary_full, "Full-distance Ironman World Championship — age-group participants & median time")),
        "img_ag_half": fig_to_base64(plot_age_groups(
            summary_half, "Ironman 70.3 World Championship — age-group participants & median time")),
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
        "img_ag_full": fig_to_base64(plot_age_groups(
            summary_full, "Regular full-distance Ironman races 2025-2026 — age-group participants & median time")),
        "img_ag_half": fig_to_base64(plot_age_groups(
            summary_half, "Regular Ironman 70.3 races 2025-2026 — age-group participants & median time")),
        "summary_full": summary_full,
        "summary_half": summary_half,
    }


def build_ireland_content() -> dict:
    """Irish triathlons, 2024-2026. Gathered in two passes: an initial pass
    (Monster Timing + Sportsplits.com), then a "full systematic sweep" against
    Triathlon Ireland's official race calendar to track down every other
    reachable timing provider for the ~150+ events that pass had missed --
    surfaced several more small/one-off RaceResult accounts plus additional
    Sportsplits.com races. Sprint/Olympic/etc mixed distances -- one combined
    age-group view, not split by distance like the Ironman tabs.
    """
    from sportsplits.parsers.raceresult.monster_timing_manifest import RACES as MT_RACES
    from sportsplits.parsers.raceresult.kerry_galway_manifest import RACES as KG_RACES
    from sportsplits.parsers.raceresult.justruns_manifest import RACES as JR_RACES
    from sportsplits.parsers.raceresult.small_races_manifest import RACES as SM_RACES
    from sportsplits.parsers.raceresult.leinster_races import RACES as LN_RR_RACES
    from sportsplits.parsers.sportsplits.manifest import RACES as SS_RACES
    from sportsplits.parsers.sportsplits.manifest_leinster import RACES as SS_LN_RACES
    from sportsplits.parsers.sportsplits.common import load_race as load_sportsplits_race

    rr_races = list(MT_RACES) + list(KG_RACES) + list(JR_RACES) + list(SM_RACES)
    races = [(r.name, load_processed_csv(r.processed_path)) for r in rr_races]
    races += [(r.name, load_processed_csv(r.processed_path)) for r in LN_RR_RACES]

    ss_race_count = 0
    for slug, name, year in list(SS_RACES) + list(SS_LN_RACES):
        for _, (event_name, df) in load_sportsplits_race(slug).items():
            races.append((f"{name} {year} - {event_name}", df))
        ss_race_count += 1

    summary = age_group_summary(races)
    total_rows = sum(len(df) for _, df in races)

    return {
        "n_monster_timing": len(MT_RACES),
        "n_raceresult_other": len(KG_RACES) + len(JR_RACES) + len(SM_RACES) + len(LN_RR_RACES),
        "n_sportsplits": ss_race_count,
        "n_events": len(races),
        "n_rows": total_rows,
        "img_ag": fig_to_base64(plot_age_groups(
            summary, "Irish Triathlons 2024-2026 — age-group participants & median time")),
        "summary": summary,
    }
