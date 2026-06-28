"""Plotting helpers shared by the web app (web.py) and the notebook (notebook.py)."""
import pandas as pd

SPLIT_COLS = ['Swim', 'T1', 'Bike', 'T2', 'Run', 'Finish']


def fmt_td(td) -> str:
    """Format a pd.Timedelta as M:SS or H:MM:SS. NaN/NaT -> 'N/A'."""
    if pd.isna(td):
        return 'N/A'
    td = pd.Timedelta(td)
    total_s = int(td.total_seconds())
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'
