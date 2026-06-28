"""Central filesystem paths for the project.

Anchoring every data path here (relative to this file, not the current working
directory) means the app, the notebook and the tests all resolve the same
locations no matter where they are launched from.
"""
from pathlib import Path

# config.py -> sportsplits -> src -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"            # source as obtained (API dumps + file-based inputs)
PROCESSED_DIR = DATA_DIR / "processed"  # generated, app-ready standard-format CSVs
