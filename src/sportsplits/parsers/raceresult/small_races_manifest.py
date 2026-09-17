"""Manifest of small Irish RaceResult events found via the public event-directory
search during the Ulster/Northwest/Midlands slice of the Triathlon-Ireland
gap-analysis sweep (2024-2026). See small_races.py for the parsing approach.

Each event was individually inspected (RaceResultClient.list_names(), then the
DataFields of the candidate list) before being added here -- not every event
found in the directory publishes usable results (see the module docstring in
the sweep report for the full list of dead ends).
"""
from sportsplits.parsers.raceresult.small_races import SmallRace

RACES = [
    SmallRace("289309", "Liam Ball Sprint & Try-A-Tri 2024",
              "Presenter/Announcer|TV Screen", "RR_LiamBall_2024.csv"),
    SmallRace("343024", "Liam Ball Sprint & Try-A-Tri 2025",
              "Presenter/Announcer|TV Screen", "RR_LiamBall_2025.csv"),
    SmallRace("358500", "Mourne Triathlon 2025",
              "Presenter/Announcer|TV Screen", "RR_Mourne_2025.csv"),
    SmallRace("354323", "Top of the Mourne Triathlon 2025",
              "Presenter/Announcer|DJ Spotter", "RR_TopOfTheMourne_2025.csv"),
    SmallRace("357881", "Lough Key Triathlon 2025",
              "Presenter/Announcer|TV Screen", "RR_LoughKey_2025.csv"),
    SmallRace("418274", "Lough Key Triathlon 2026",
              "Presenter/Announcer|TV Screen", "RR_LoughKey_2026.csv"),
    SmallRace("348819", "Telus Liquid Motion Triathlon 2025",
              "Presenter/Announcer|TV Screen", "RR_LiquidMotion_2025.csv"),
    SmallRace("340008", "Roe Valley Triathlon 2025",
              "Result Lists|Full Results", "RR_RoeValley_2025.csv", contests=()),
    SmallRace("295541", "Tri an Mhi Sprint & Standard Triathlon 2024",
              "Result Lists|Overall Results", "RR_TriAnMhi_2024.csv", contests=("1", "2")),
    SmallRace("348820", "Sheephaven Half Ironman & Sprint 2025",
              "Result Lists|Age Group Results - Win", "RR_Sheephaven_2025.csv",
              finish_only=True),
]

# Confirmed dead ends (event exists in the RaceResult directory but publishes
# no usable results -- don't re-check these event ids):
#   Sheephaven 2024 (297335): config exists, list_names() is empty.
#   Roe Valley 2026 (398239): config exists, list_names() is empty (race hadn't
#     happened relative to when the account was set up, or results never got
#     published in this list format).
#   Liam Ball 2026 (401070): same, empty list_names().
#   Lough Key 2024 (306402): same, empty list_names().
#   Telus Liquid Motion 2024 (301068): same, empty list_names().
#   Top of the Mourne 2026 (418355): config endpoint itself 404s (account
#     likely deleted/rebuilt under a different id after the event).


def build_all() -> dict:
    from sportsplits.parsers.raceresult.small_races import build_all as _build_all
    return _build_all(RACES)
