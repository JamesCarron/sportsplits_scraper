"""Kerry + Galway RaceResult events gathered in the "full systematic sweep" of
Triathlon Ireland's 2024-2026 calendar gaps. See kerry_galway.py for the two
account styles ("inline" vs "agejoin") these events split into.

Found via RaceResultClient.search_events() against the public my.raceresult.com
event directory (the same endpoint the app's own "Search" add-race feature
uses) -- no site-specific scraping involved, just RaceResult's own public API.
"""
from sportsplits.parsers.raceresult.kerry_galway import KerryGalwayRace

RACES = [
    # ── Inline style (SEX + age-group band already in the results list) ─────
    KerryGalwayRace(
        event_id="299197", name="Hardman Waterville Triathlon 2024",
        processed_filename="KG_HardmanWaterville_2024.csv",
        listname="Result Lists|Full Results", keep_prefixes=("#1_",),
    ),
    KerryGalwayRace(
        event_id="306008", name="Hardman Killarney Triathlon 2024",
        processed_filename="KG_HardmanKillarney_2024.csv",
        listname="Result Lists|Full Results", keep_prefixes=("#1_",),
    ),
    KerryGalwayRace(
        event_id="308173", name="Cromane Seafest Sprint Triathlon 2024",
        processed_filename="KG_CromaneSeafest_2024.csv",
        listname="Result Lists|Full Results", keep_prefixes=("#1_",),
    ),
    KerryGalwayRace(
        event_id="295572", name="Ballinskelligs Sprint & Olympic Triathlon 2025",
        processed_filename="KG_Ballinskelligs_2025.csv",
        listname="Result Lists|Full Results", keep_prefixes=("#1_", "#2_"),
    ),
    KerryGalwayRace(
        event_id="302998", name="Tri Lakes Clonbur Triathlon 2024",
        processed_filename="KG_TriLakesClonbur_2024.csv",
        listname="Presenter/Announcer|TV Screen", contest="1", keep_prefixes=("#1_",),
    ),
    KerryGalwayRace(
        event_id="355016", name="Tri Lakes Clonbur Triathlon 2025",
        processed_filename="KG_TriLakesClonbur_2025.csv",
        listname="Presenter/Announcer|TV Screen", contest="1", keep_prefixes=("#1_",),
    ),
    KerryGalwayRace(
        event_id="412523", name="Loughrea Triathlon Festival 2026 - Sprint",
        processed_filename="KG_LoughreaFestival_2026.csv",
        listname="Result Lists|Triathlon Detail", page="list2", contest="7",
        keep_prefixes=("#1_",),
    ),

    # ── Agejoin style (splits list has no SEX column; joined against a
    #    separate id-keyed Age Group list for sex/year/club) ─────────────────
    KerryGalwayRace(
        event_id="349584", name="Hardman Waterville Triathlon 2025",
        processed_filename="KG_HardmanWaterville_2025.csv",
        listname="Online|Final", keep_prefixes=("#1_",), name_format="lastfirst",
        race_year=2025, ag_list="Result Lists|Age Group3 Results-Win",
    ),
    KerryGalwayRace(
        event_id="363509", name="Hardman Valentia Island Triathlon 2025",
        processed_filename="KG_HardmanValentia_2025.csv",
        listname="Online|Final", contest="1", keep_prefixes=("#1_",), name_format="lastfirst",
        race_year=2025, ag_list="Result Lists|Age Group2 Results - Win",
    ),
    KerryGalwayRace(
        event_id="402707", name="Ballinskelligs Sprint & Olympic Triathlon 2026",
        processed_filename="KG_Ballinskelligs_2026.csv",
        listname="Online|Final", keep_prefixes=("#1_", "#2_"), name_format="lastfirst",
        race_year=2026, ag_list="Result Lists|Age Group Results - Win",
    ),
]

_names = [r.name for r in RACES]
assert len(_names) == len(set(_names)), f"Duplicate names in RACES: {_names}"
