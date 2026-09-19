"""Regenerate data/cache/age_group_content.pkl, the Age-Group Analysis page's
prebaked content (age_group_page.build_all_content()/save_cache()).

Run this after adding/changing any race data the page reads (Ironman World
Championship, regular Ironman, or Ireland sources) or after changing
age_group_page.py's build_*_content() functions, then commit the resulting
.pkl file -- app.py loads it instead of recomputing from scratch at every
startup, which otherwise takes 100+ seconds (mostly parsing 251 regular
Ironman races' raw JSON).

    python scripts/prebake_age_group.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sportsplits.age_group_page import save_cache, CACHE_PATH


def main() -> None:
    t0 = time.time()
    save_cache()
    print(f"Wrote {CACHE_PATH} in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
