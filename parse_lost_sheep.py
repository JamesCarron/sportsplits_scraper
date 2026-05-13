import pandas as pd


_GENDER_TO_CLASS = {'Male': 'Open', 'Female': 'Female'}

# Pos values that indicate a non-finisher; no times or gender recorded in source
_NON_FINISH_STATUSES = {'DNS', 'DNF', 'DQ', 'NYS'}


def _parse_timedelta(series: pd.Series) -> pd.Series:
    """Convert '0 days HH:MM:SS' strings to pd.Timedelta, NaT for missing."""
    return pd.to_timedelta(series, errors='coerce')


def load_results(path: str = 'lost_sheep_2025_results.csv') -> pd.DataFrame:
    raw = pd.read_csv(path, dtype={'Pos': str, 'Number': str})

    rows = []
    for _, r in raw.iterrows():
        place_str = str(r['Pos']).strip().upper()
        is_non_finish = place_str in _NON_FINISH_STATUSES

        place = None if is_non_finish else (int(place_str) if place_str.isdigit() else None)

        # Non-finishers carry their status (DNS/DNF/DQ/NYS) as the Class value
        # so they remain in the DataFrame but are excluded from metrics groupings
        if is_non_finish:
            cls = place_str
        else:
            cls = _GENDER_TO_CLASS.get(str(r['Gender']).strip(), '')

        cat_pos = r.get('Category_Pos')
        grp_rank = int(cat_pos) if pd.notna(cat_pos) else None

        rows.append({
            'Place':      place,
            'Bib':        0,                                    # not present in source
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
        out[col] = _parse_timedelta(out[col])

    return out


if __name__ == '__main__':
    df = load_results()
    pd.set_option('display.max_columns', 20)
    pd.set_option('display.width', None)
    print(f'Rows: {len(df)}')
    print(df.head(10))
    print('\nDNS rows:')
    print(df[df['Place'].isna()][['Place', 'Name', 'Class', 'Finish']].head())
    print('\nClass counts:', df['Class'].value_counts().to_dict())
    print('Age groups:', sorted(df['Age_Group'].unique()))
