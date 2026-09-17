"""Races gathered from sportsplits.com. Each entry: (slug, display name, year).
Raw data: data/raw/sportsplits/<slug>.json (scraped via browser -- see common.py
docstring). Discovery here was time-boxed and is NOT an exhaustive sweep of every
Irish triathlon on the platform -- sportsplits.com's own search only surfaces one
"best match" per query rather than listing all editions of a recurring race, so
finding everything requires guessing name+year search terms one at a time. This
list should grow incrementally as more races are searched and scraped the same
way, not by re-deriving the discovery method each time.

Confirmed NOT present on sportsplits.com for 2024-2026 (searched, no hit in range,
don't re-search these): Vodafone Dublin City Triathlon (only a 2023 edition found),
TriAthy (only 2019/2022/2023/2025 -- 2025 is the one above; no 2024 or 2026),
Wicklow Triathlon (only a 2014 edition), Tribesman Triathlon, National Triathlon
Championships, Portumna Triathlon, Gorey Triathlon, and a dozen other guessed
names (Athlone/Cong/Connemara/Waterford/Mosney/Celtic Man/Sligo/Belfast/Lough
Cutra/Emo) -- these are presumably timed by another provider (e.g. Monster
Timing) or don't publish results on Sportsplits.

SCRAPED BUT NOT YET SAVED TO DISK -- browser downloads to this domain got
silently blocked by Chrome after the very first one (same one-time
per-origin issue hit earlier for coachcox.co.uk in this project; needs the user
to allow automatic downloads for sportsplits.com once, the same fix that worked
before). The scraped data was still sitting in the browser tab's `window`
variables (__skerries_clean, __kilkenny_clean, __hotw2025_clean,
__hotw2026_clean) when this fork stopped -- if that tab is still open, re-running
the same download step will work immediately once downloads are allowed;
otherwise these need a quick re-scrape (a couple minutes each, not a rediscovery
job -- see the confirmed slugs/events below):
  - skerries-triathlon-2024-2024, event 1 "Sprint Tri" only (492 rows). Events
    2 (Aqua Bike) and 3-7 (Junior/school-age categories) intentionally excluded.
  - kilkenny-triathlon-2025, events 1 "TryaTri" (59 rows) + 2 "Sprint Tri" (150
    rows). Event 3 "Relay" intentionally excluded.
  - hell-of-the-west-2025, event 1 "Individuals" (259 rows, confirmed via
    Swim/T1/Cycle/T2/Run columns -- it IS a triathlon despite the name). Event
    2 "Team" intentionally excluded.
  - hell-of-the-west-2026, event 1 "Individuals" (346 rows). Event 2 "Team"
    intentionally excluded.
No 2024 edition of Kilkenny Triathlon or Hell of the West was found (Kilkenny:
2021/2022/2023/2025 only; Hell of the West: 2022/2023/2025/2026 only).
"""

RACES = [
    ("triathy-2025-2025", "Triathy", 2025),
    ("cork-city-triathlon-2024", "Cork City Triathlon", 2024),
    ("skerries-triathlon-2024-2024", "Skerries Triathlon", 2024),
    ("kilkenny-triathlon-2025", "Kilkenny Triathlon", 2025),
    ("hell-of-the-west-2025", "Hell of the West", 2025),
    ("hell-of-the-west-2026", "Hell of the West", 2026),
]

# Cork City Triathlon's sub-events actually pulled (see common.py's load_race --
# it returns ALL events in the raw JSON; the raw file for this race only
# contains these 6, the true triathlon distances, not Duathlon/Aqua
# Bike/Youth Series which were skipped during scraping):
#   1 Junior Cup Male, 2 Elite Men, 3 Elite Female, 4 National Series Sprint,
#   8 Try a Tri, 9 Junior Cup Female
