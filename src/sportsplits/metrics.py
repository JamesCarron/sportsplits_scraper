import pandas as pd

SPLIT_COLS = ['Swim', 'T1', 'Bike', 'T2', 'Run', 'Finish']


def add_percentiles(df: pd.DataFrame) -> pd.DataFrame:
    """Add class-wide and age-group percentile columns for each split."""
    df = df.copy()
    for col in SPLIT_COLS:
        df[f'{col}_pct_class'] = (
            df.groupby('Class')[col]
              .rank(pct=True, ascending=False, na_option='keep') * 100
        ).round(1)
        df[f'{col}_pct_ag'] = (
            df.groupby(['Class', 'Age_Group'])[col]
              .rank(pct=True, ascending=False, na_option='keep') * 100
        ).round(1)
    return df


def add_overall_percentiles(df: pd.DataFrame) -> pd.DataFrame:
    """Add race-wide percentile columns (all classes combined) for each split."""
    df = df.copy()
    for col in SPLIT_COLS:
        df[f'{col}_pct_overall'] = (
            df[col]
              .rank(pct=True, ascending=False, na_option='keep') * 100
        ).round(1)
    return df


def add_normalised_percentiles(df: pd.DataFrame, base: str = 'pct_class') -> pd.DataFrame:
    """
    Add split percentiles normalised to each athlete's best split percentile.

    Each normalised value = split_pct / best_split_pct * 100, so 100 means
    the split is as strong as the athlete's best split, <100 means it is weaker.
    `base` selects which percentile family to normalise against ('pct_class',
    'pct_ag', or 'pct_overall').
    """
    df = df.copy()
    src_cols = [f'{col}_{base}' for col in SPLIT_COLS]
    missing = [c for c in src_cols if c not in df.columns]
    if missing:
        raise ValueError(f'Source columns not found (run the matching add_* function first): {missing}')

    best = df[src_cols].max(axis=1)
    for col in SPLIT_COLS:
        src = f'{col}_{base}'
        df[f'{col}_pct_norm'] = (df[src].div(best) * 100).round(1)
    return df


def build_metrics_from_df(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all metric calculations to an already-loaded DataFrame."""
    df = add_percentiles(df)
    df = add_overall_percentiles(df)
    df = add_normalised_percentiles(df)
    return df


if __name__ == '__main__':
    pass
    pct_cols = [c for c in df.columns if '_pct_' in c]
    print(df[['Name', 'Class', 'Age_Group'] + pct_cols].head(20))
