"""Launch the Triathlon Results Analyser without installing the package.

Puts src/ on the import path, then starts the Dash server:

    python run.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from sportsplits.app import main

if __name__ == "__main__":
    main()
