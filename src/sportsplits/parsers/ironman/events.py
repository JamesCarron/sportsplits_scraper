"""Built-in Ironman World Championship races -- the last decade (2016-2025) of the
full-distance Ironman World Championship and the Ironman 70.3 World Championship,
covering both genders and both distances.

Raw source: CoachCox's IMStats JSON API (see common.py for the fetch/format notes).
Gaps (2020/2021 full-distance, 2020 70.3) are COVID cancellations, not omissions.

2022's full-distance race is a genuine exception to "one race = one gender": Kona
that year ran as two days split by *age-group division*, not cleanly by gender
(each day mixes some male AG divisions with the rest of the field) -- so it keeps
CoachCox's neutral "Day 1"/"Day 2" naming rather than a "(Men)"/"(Women)" label
that would misrepresent who actually raced each day.
"""
from sportsplits.parsers.ironman.common import IronmanEventSpec, slugify

BUILTIN_EVENTS = [
    # ── Ironman World Championship (full distance) ──────────────────────────
    IronmanEventSpec(race_id="346",  name="IM WC Kona 2016",            distance="full", processed_filename="IM_WC_Kona_2016.csv"),
    IronmanEventSpec(race_id="408",  name="IM WC Kona 2017",            distance="full", processed_filename="IM_WC_Kona_2017.csv"),
    IronmanEventSpec(race_id="459",  name="IM WC Kona 2018",            distance="full", processed_filename="IM_WC_Kona_2018.csv"),
    IronmanEventSpec(race_id="502",  name="IM WC Kona 2019",            distance="full", processed_filename="IM_WC_Kona_2019.csv"),
    IronmanEventSpec(race_id="1803", name="IM WC Kona Day 1 2022",      distance="full", processed_filename="IM_WC_Kona_Day1_2022.csv"),
    IronmanEventSpec(race_id="1879", name="IM WC Kona Day 2 2022",      distance="full", processed_filename="IM_WC_Kona_Day2_2022.csv"),
    IronmanEventSpec(race_id="2185", name="IM WC Kona (Women) 2023",    distance="full", processed_filename="IM_WC_Kona_Women_2023.csv"),
    IronmanEventSpec(race_id="2186", name="IM WC Nice (Men) 2023",      distance="full", processed_filename="IM_WC_Nice_Men_2023.csv"),
    IronmanEventSpec(race_id="2173", name="IM WC Kona (Men) 2024",      distance="full", processed_filename="IM_WC_Kona_Men_2024.csv"),
    IronmanEventSpec(race_id="2180", name="IM WC Nice (Women) 2024",    distance="full", processed_filename="IM_WC_Nice_Women_2024.csv"),
    IronmanEventSpec(race_id="2202", name="IM WC Nice (Men) 2025",      distance="full", processed_filename="IM_WC_Nice_Men_2025.csv"),
    IronmanEventSpec(race_id="2203", name="IM WC Kona (Women) 2025",    distance="full", processed_filename="IM_WC_Kona_Women_2025.csv"),

    # ── Ironman 70.3 World Championship (half distance) ─────────────────────
    IronmanEventSpec(race_id="393",  name="IM 70.3 WC Mooloolaba 2016",              distance="70.3", processed_filename="IM_703_WC_Mooloolaba_2016.csv"),
    IronmanEventSpec(race_id="467",  name="IM 70.3 WC Chattanooga (Men) 2017",       distance="70.3", processed_filename="IM_703_WC_Chattanooga_Men_2017.csv"),
    IronmanEventSpec(race_id="2659", name="IM 70.3 WC Chattanooga (Women) 2017",     distance="70.3", processed_filename="IM_703_WC_Chattanooga_Women_2017.csv"),
    IronmanEventSpec(race_id="2658", name="IM 70.3 WC Nelson Mandela Bay (Men) 2018",   distance="70.3", processed_filename="IM_703_WC_NelsonMandelaBay_Men_2018.csv"),
    IronmanEventSpec(race_id="466",  name="IM 70.3 WC Nelson Mandela Bay (Women) 2018", distance="70.3", processed_filename="IM_703_WC_NelsonMandelaBay_Women_2018.csv"),
    IronmanEventSpec(race_id="2657", name="IM 70.3 WC Nice (Men) 2019",              distance="70.3", processed_filename="IM_703_WC_Nice_Men_2019.csv"),
    IronmanEventSpec(race_id="617",  name="IM 70.3 WC Nice (Women) 2019",            distance="70.3", processed_filename="IM_703_WC_Nice_Women_2019.csv"),
    IronmanEventSpec(race_id="1743", name="IM 70.3 WC St. George 2021",              distance="70.3", processed_filename="IM_703_WC_StGeorge_2021.csv"),
    IronmanEventSpec(race_id="2656", name="IM 70.3 WC St. George (Men) 2022",        distance="70.3", processed_filename="IM_703_WC_StGeorge_Men_2022.csv"),
    IronmanEventSpec(race_id="1524", name="IM 70.3 WC St. George (Women) 2022",      distance="70.3", processed_filename="IM_703_WC_StGeorge_Women_2022.csv"),
    IronmanEventSpec(race_id="2655", name="IM 70.3 WC Lahti (Men) 2023",             distance="70.3", processed_filename="IM_703_WC_Lahti_Men_2023.csv"),
    IronmanEventSpec(race_id="2652", name="IM 70.3 WC Lahti (Women) 2023",           distance="70.3", processed_filename="IM_703_WC_Lahti_Women_2023.csv"),
    IronmanEventSpec(race_id="2654", name="IM 70.3 WC Taupo (Men) 2024",             distance="70.3", processed_filename="IM_703_WC_Taupo_Men_2024.csv"),
    IronmanEventSpec(race_id="2653", name="IM 70.3 WC Taupo (Women) 2024",           distance="70.3", processed_filename="IM_703_WC_Taupo_Women_2024.csv"),
    IronmanEventSpec(race_id="2662", name="IM 70.3 WC Marbella (Men) 2025",          distance="70.3", processed_filename="IM_703_WC_Marbella_Men_2025.csv"),
    IronmanEventSpec(race_id="2661", name="IM 70.3 WC Marbella (Women) 2025",        distance="70.3", processed_filename="IM_703_WC_Marbella_Women_2025.csv"),
]

# Guard against accidental duplicate names/ids.
_names = [e.name for e in BUILTIN_EVENTS]
assert len(_names) == len(set(_names)), f"Duplicate event names in BUILTIN_EVENTS: {_names}"
_ids = [e.race_id for e in BUILTIN_EVENTS]
assert len(_ids) == len(set(_ids)), f"Duplicate race ids in BUILTIN_EVENTS: {_ids}"

EVENTS = BUILTIN_EVENTS


def build_all() -> dict:
    """Process every built-in Ironman race. Returns {name: processed_csv_path}."""
    from sportsplits.parsers.ironman.common import process_all
    return process_all(EVENTS)
