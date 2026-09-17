"""Manifest of Irish triathlon races timed by Monster Timing (monstertiming.ie),
2025/2026 (no 2024 -- see monster_timing.py module docstring). Each entry is one
(event, contest) pair -- one distance/category at one event.

Discovered by walking monstertiming.ie/race-results/ for data-type=5 (Triathlon)
events, then inspecting each event's actual RaceResult config (published lists,
contests) directly -- list names and whether a `contest` query param is
required turned out to be genuinely per-event (organiser-configured), not a
fixed convention, so each entry here was individually verified, not guessed
from a template. Relay and Aquabike (swim+bike only, no run) contests are
excluded -- not individual triathlon results.

Two secondary contests (Lough Ree 2025's Try-A-Tri, Tribesman 2025's Try-A-Tri)
are real gaps, not oversights: their account only publishes contest 1 through
the public list -- fetching without a contest param returns only contest 1's
data, and fetching with an explicit contest param 404s outright for this
account. No accessible path to that data was found.
"""
from sportsplits.parsers.raceresult.monster_timing import MonsterTimingRace

RACES = [
    MonsterTimingRace("348909", "1", "Lough Ree Monster Triathlon 2025 - Sprint",
                       "Online|Final", "MT_LoughRee_2025_Sprint.csv", needs_contest_param=False),
    MonsterTimingRace("350467", "1", "Peninsula Sea Sprint 2025",
                       "Online|Final", "MT_PeninsulaSeaSprint_2025.csv", needs_contest_param=False),
    MonsterTimingRace("323083", "1", "Tribesman Triathlon 2025 - National Series Sprint",
                       "Online|Final", "MT_Tribesman_2025_Sprint.csv", needs_contest_param=False),
    MonsterTimingRace("396256", "1", "Athlone Tri Club I Tri'd Triathlon 2026 - Try-A-Tri",
                       "Online|Final Results", "MT_Athlone_2026_TryATri.csv", needs_contest_param=True),
    MonsterTimingRace("391493", "1", "King of the Hill Triathlon 2026 - Sprint",
                       "Online|Final", "MT_KingOfTheHill_2026_Sprint.csv", needs_contest_param=True),
    MonsterTimingRace("399025", "1", "Lough Ree Monster Triathlon 2026 - Sprint",
                       "Result Lists|Final Online Results", "MT_LoughRee_2026_Sprint.csv", needs_contest_param=True),
    MonsterTimingRace("399025", "2", "Lough Ree Monster Triathlon 2026 - Try-A-Tri",
                       "Result Lists|Final Online Results", "MT_LoughRee_2026_TryATri.csv", needs_contest_param=True),
    MonsterTimingRace("414920", "1", "Peninsula Sea Sprint 2026",
                       "Result Lists|Final Online Results", "MT_PeninsulaSeaSprint_2026.csv", needs_contest_param=True),
    MonsterTimingRace("372584", "1", "Telus Salmon Run Triathlon 2026 - Sprint",
                       "Result Lists|Overall Results - Sprint", "MT_TelusSalmonRun_2026_Sprint.csv", needs_contest_param=True),
    MonsterTimingRace("391498", "1", "The Lost Sheep Triathlon 2026 - Middle Distance",
                       "Result Lists|Race Category Results", "MT_LostSheep_2026.csv", needs_contest_param=True),
    MonsterTimingRace("372579", "1", "Tri Lakes Connemara Sprint Triathlon 2026",
                       "Online|Final", "MT_TriLakesConnemara_2026.csv", needs_contest_param=True),
    MonsterTimingRace("355714", "1", "Tribesman Triathlon 2026 - National Series Sprint",
                       "Online|Final", "MT_Tribesman_2026_Sprint.csv", needs_contest_param=False),
    MonsterTimingRace("378037", "1", "Westport Triathlon 2026 - Olympic",
                       "Result Lists|Final Online Results", "MT_Westport_2026_Olympic.csv", needs_contest_param=True),
    MonsterTimingRace("378037", "2", "Westport Triathlon 2026 - Super Sprint",
                       "Result Lists|Age Group Results Super Sprint", "MT_Westport_2026_SuperSprint.csv", needs_contest_param=True),
]

_names = [r.name for r in RACES]
assert len(_names) == len(set(_names)), f"Duplicate race names: {_names}"


def build_all() -> dict:
    """Fetch + process every Monster Timing race. Returns {name: processed_csv_path}."""
    from sportsplits.parsers.raceresult.monster_timing import build_race
    return {race.name: build_race(race) for race in RACES}
