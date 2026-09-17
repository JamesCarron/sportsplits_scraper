"""Additional Sportsplits.com races found during the Triathlon Ireland calendar
gap-analysis sweep (Leinster/East slice) -- kept separate from the existing
manifest.py (which is shared infrastructure from an earlier pass) so the two
can be merged without edit conflicts.

Same tuple format as manifest.py: (slug, display name, year). load_race()
from sportsplits.parsers.sportsplits.common handles the actual parsing --
these are just new raw JSON files under data/raw/sportsplits/.
"""

RACES = [
    ("rdj-dublin-city-triathlon-2025", "RDJ Dublin City Triathlon", 2025),
    ("rdj-dublin-city-triathlon-2026", "RDJ Dublin City Triathlon", 2026),
    ("pikeman-triathlon-2025", "Pikeman Triathlon", 2025),
    ("two-provence-triathlon-2025-2025", "Two Provinces Triathlon", 2025),
    ("two-provence-triathlon-2026", "Two Provinces Triathlon", 2026),
    # Waterford, flagged during the Ulster/Northwest sweep slice as reachable
    # on Sportsplits (out of that agent's scope to add) -- only Sprint (event 1)
    # and Olympic (event 3) individual results pulled; Sprint/Olympic Relay and
    # Youth Series events on the same race skipped, same as every other manifest
    # here (adult individual triathlon only).
    ("tried-and-tested-dungarvan-triathlon-2024", "Tried and Tested Dungarvan Triathlon", 2024),
]
