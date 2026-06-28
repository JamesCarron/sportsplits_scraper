"""Parser for the CTC Lost Sheep 2025 results CSV.

A flat CSV export (not a RaceResult event); returns the standard 13-column format
described in data_format.md.
"""
import pandas as pd

_GENDER_TO_CLASS = {'Male': 'Open', 'Female': 'Female'}
_NON_FINISH_STATUSES = {'DNS', 'DNF', 'DQ', 'NYS'}


def load_results(path: str) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype={'Pos': str, 'Number': str})

    rows = []
    for _, r in raw.iterrows():
        place_str = str(r['Pos']).strip().upper()
        is_non_finish = place_str in _NON_FINISH_STATUSES

        place = None if is_non_finish else (int(place_str) if place_str.isdigit() else None)

        if is_non_finish:
            cls = place_str
        else:
            cls = _GENDER_TO_CLASS.get(str(r['Gender']).strip(), '')

        cat_pos = r.get('Category_Pos')
        grp_rank = int(cat_pos) if pd.notna(cat_pos) else None

        rows.append({
            'Place':      place,
            'Bib':        0,
            'Name':       str(r['Name']).strip(),
            'Age_Group':  str(r['Category']).strip() if pd.notna(r['Category']) else '',
            'Group_Rank': grp_rank,
            'Class':      cls,
            'Club':       str(r['Club']).strip() if pd.notna(r['Club']) else '',
            'Swim':       r['Swim'],
            'T1':         r['T1'],
            'Bike':       r['Cycle'],
            'T2':         r['T2'],
            'Run':        r['Run'],
            'Finish':     r['Gun Time'],
        })

    out = pd.DataFrame(rows)

    for col in ['Swim', 'T1', 'Bike', 'T2', 'Run', 'Finish']:
        out[col] = pd.to_timedelta(out[col], errors='coerce')

    return out
