"""Aggregate cross-race analysis: age-group competitiveness and slowest-pro-female
outlier analysis. Pure functions over [(race_name, df), ...] pairs (df = standard
13-column format), decoupled from where the races came from -- used by the Ironman
World Championship, regular-races, and Ireland views on the Age-Group Analysis page.
"""
import re

import pandas as pd

AG_ORDER = ["18-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54",
            "55-59", "60-64", "65-69", "70-74", "75-79", "80-84"]

# Only genuine 5-year age bands (e.g. "25-29"), not custom wide buckets some
# sources use for smaller categories (e.g. Monster Timing's "20-34"/"50+").
_BAND_RE = r"^\d{1,2}-\d{1,2}$"


def _ag_sort_key(band: str) -> int:
    return AG_ORDER.index(band) if band in AG_ORDER else 99


def age_group_summary(races: list) -> pd.DataFrame:
    """races: [(name, df), ...]. Returns Gender/Band/n/median/mean/std, band-ordered.

    Gender comes from Class (Open->Male, Female->Female) -- the one field every
    source in this app already normalizes consistently -- not parsed out of
    Age_Group, since only Ironman's Age_Group carries a gender prefix ("M25-29");
    Sportsplits/Monster Timing's is just the band ("25-29"), gender is separate.
    """
    frames = []
    for name, df in races:
        d = df.copy()
        d["__race"] = name
        frames.append(d)
    all_df = pd.concat(frames, ignore_index=True)

    all_df["Gender"] = all_df["Class"].map({"Open": "Male", "Female": "Female"})
    # Strip a leading gender letter before a digit if present (Ironman's "M25-29"),
    # otherwise the band is already bare (Sportsplits/Monster Timing's "25-29").
    band = all_df["Age_Group"].astype(str).str.replace(r"^[MF](?=\d)", "", regex=True).str.strip()
    ag = all_df[all_df["Gender"].notna() & band.str.match(_BAND_RE, na=False) & all_df["Finish"].notna()].copy()
    ag["Band"] = band[ag.index]

    summary = (
        ag.groupby(["Gender", "Band"])["Finish"]
        .agg(n="count", median="median", mean="mean", std="std")
        .reset_index()
    )
    summary["order"] = summary["Band"].map(_ag_sort_key)
    summary = summary.sort_values(["Gender", "order"]).drop(columns="order")
    return summary


# Ordered distance/format buckets, most-specific pattern first so e.g. "Super
# Sprint" is claimed before the plainer "Sprint" pattern gets a chance at it
# (matched text is masked out before moving to the next pattern, so a name
# like "Westport Triathlon - Super Sprint" doesn't also register a "Sprint"
# hit for the substring it already claimed).
_DISTANCE_PATTERNS = [
    ("Try-a-Tri", re.compile(r"try[\s-]?a[\s-]?tri|i\s*tri'?d", re.I)),
    ("Super Sprint", re.compile(r"super\s*sprint", re.I)),
    ("Sprint", re.compile(r"\bsprint\b", re.I)),
    ("Olympic / Standard", re.compile(r"\bolympic\b|\bstandard\b", re.I)),
    ("Middle / Half", re.compile(r"\bmiddle\b|\bhalf\b|\b70\.3\b", re.I)),
    ("Full / Long", re.compile(r"\bfull\b|\blong distance\b|\bironman\b", re.I)),
    ("Duathlon", re.compile(r"duathlon", re.I)),
    ("Aquabike", re.compile(r"aqua\s*bike", re.I)),
]
_RELAY_RE = re.compile(r"\brelay\b", re.I)

# Display order for whatever buckets actually turn up in a given dataset.
DISTANCE_ORDER = [
    "Try-a-Tri", "Super Sprint", "Sprint", "Olympic / Standard", "Middle / Half",
    "Full / Long", "Duathlon", "Aquabike", "Relay",
    "Mixed (multiple distances combined)", "Other / Unspecified",
]


def classify_distance(name: str) -> str:
    """Best-effort distance/format bucket from a race (+ event) name, e.g.
    "Cromane Seafest Sprint Triathlon 2024" -> "Sprint". Team relay events are
    called out on their own regardless of any distance word also present (the
    relay format, not the per-leg distance, is what sets them apart from the
    individual age-group data the rest of this app assumes). A name carrying
    more than one distance word (e.g. "Ballinskelligs Sprint & Olympic
    Triathlon") means that race's results list is genuinely a single combined
    table across distances, not separable after the fact -- flagged as
    "Mixed" rather than silently assigned to one of them.
    """
    if _RELAY_RE.search(name):
        return "Relay"
    text = name
    hits = []
    for label, pattern in _DISTANCE_PATTERNS:
        if pattern.search(text):
            hits.append(label)
            text = pattern.sub(" ", text)
    if not hits:
        return "Other / Unspecified"
    if len(hits) > 1:
        return "Mixed (multiple distances combined)"
    return hits[0]


def slowest_pro_female(races: list, race_dates: dict | None = None):
    """races: [(name, df), ...]. Excludes finishers beyond Q3+1.5*IQR (per race) among
    the pro (FPRO) women's field -- the outlier fence for "obviously had an issue".
    Returns (per-race result df, avg_raw, avg_clean). Races with no pro field are skipped.
    """
    rows = []
    for name, df in races:
        g = df[(df["Class"] == "Female") & (df["Age_Group"] == "FPRO") & df["Finish"].notna()]
        if g.empty:
            continue
        finishes = g["Finish"].dt.total_seconds()
        q1, q3 = finishes.quantile([0.25, 0.75])
        iqr = q3 - q1
        upper_fence = q3 + 1.5 * iqr
        clean = g[finishes <= upper_fence]
        outliers = g[finishes > upper_fence]

        raw_slowest = g.loc[finishes.idxmax()]
        clean_slowest = clean.loc[clean["Finish"].dt.total_seconds().idxmax()] if not clean.empty else None

        rows.append({
            "race": name,
            "n_pros": len(g),
            "n_excluded_outliers": len(outliers),
            "raw_slowest": raw_slowest["Finish"],
            "clean_slowest": clean_slowest["Finish"] if clean_slowest is not None else pd.NaT,
        })

    result = pd.DataFrame(rows)
    if result.empty:
        return result, pd.NaT, pd.NaT

    if race_dates:
        result["date"] = pd.to_datetime(result["race"].map(race_dates))
        result = result.sort_values("date")
    else:
        result = result.sort_values("race")

    avg_raw = pd.to_timedelta(result["raw_slowest"]).mean()
    avg_clean = pd.to_timedelta(result["clean_slowest"]).mean()
    return result, avg_raw, avg_clean


# Actual World Championship race dates (not just year) -- e.g. in 2023-2025 Nice ran in
# September and Kona in October, so a plain year-sort would misorder them within a year.
# Source: coachcox.co.uk series listings.
WC_RACE_DATES = {
    "IM WC Kona 2016": "2016-10-08", "IM WC Kona 2017": "2017-10-14",
    "IM WC Kona 2018": "2018-10-13", "IM WC Kona 2019": "2019-10-12",
    "IM WC Kona Day 1 2022": "2022-10-06", "IM WC Kona Day 2 2022": "2022-10-08",
    "IM WC Nice (Men) 2023": "2023-09-10", "IM WC Kona (Women) 2023": "2023-10-14",
    "IM WC Nice (Women) 2024": "2024-09-22", "IM WC Kona (Men) 2024": "2024-10-26",
    "IM WC Nice (Men) 2025": "2025-09-14", "IM WC Kona (Women) 2025": "2025-10-11",

    "IM 70.3 WC Mooloolaba 2016": "2016-09-04",
    "IM 70.3 WC Chattanooga (Women) 2017": "2017-09-09",
    "IM 70.3 WC Chattanooga (Men) 2017": "2017-09-10",
    "IM 70.3 WC Nelson Mandela Bay (Women) 2018": "2018-09-01",
    "IM 70.3 WC Nelson Mandela Bay (Men) 2018": "2018-09-02",
    "IM 70.3 WC Nice (Women) 2019": "2019-09-07", "IM 70.3 WC Nice (Men) 2019": "2019-09-08",
    "IM 70.3 WC St. George 2021": "2021-09-18",
    "IM 70.3 WC St. George (Women) 2022": "2022-10-28",
    "IM 70.3 WC St. George (Men) 2022": "2022-10-29",
    "IM 70.3 WC Lahti (Women) 2023": "2023-08-26", "IM 70.3 WC Lahti (Men) 2023": "2023-08-27",
    "IM 70.3 WC Taupo (Women) 2024": "2024-12-14", "IM 70.3 WC Taupo (Men) 2024": "2024-12-15",
    "IM 70.3 WC Marbella (Women) 2025": "2025-11-08", "IM 70.3 WC Marbella (Men) 2025": "2025-11-09",
}
