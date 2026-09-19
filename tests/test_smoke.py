"""End-to-end smoke tests for the restructured package.

These read the committed processed CSVs in data/processed/ (no network), so they
exercise the full registry -> loader -> metrics path and the Dash app factory.
"""
from sportsplits.app import create_app
from sportsplits.races import REGISTRY, _LAZY_LOAD_NAMES, get_race_df, load_all


def test_load_all_returns_every_eager_race_with_metrics():
    """load_all() deliberately skips the 251 regular Ironman races (see
    races._LAZY_LOAD_NAMES) -- they're registered/selectable but only loaded
    on first selection (get_race_df()), since parsing all of them upfront
    added 80+ seconds to every app startup."""
    dfs = load_all()
    assert set(dfs) == set(REGISTRY) - _LAZY_LOAD_NAMES
    assert len(dfs) == 35
    for name, df in dfs.items():
        assert len(df) > 0, f"{name} loaded no rows"
        assert df.shape[1] == 37, f"{name} has {df.shape[1]} columns, expected 37"


def test_lazy_races_registered_but_not_eagerly_loaded():
    dfs = load_all()
    assert _LAZY_LOAD_NAMES, "expected at least one lazy-loaded race"
    for name in _LAZY_LOAD_NAMES:
        assert name in REGISTRY
        assert name not in dfs


def test_get_race_df_lazy_loads_and_caches():
    dfs = load_all()
    name = next(iter(_LAZY_LOAD_NAMES))
    assert name not in dfs

    df = get_race_df(dfs, name)
    assert len(df) > 0
    assert name in dfs
    assert get_race_df(dfs, name) is df


def test_identity_swap_applied():
    """The known Fastnet 2026 identity mix-up is corrected in the processed data."""
    row = load_all()["Fastnet Sprint 2026"].query("Name == 'James Carron'")
    assert not row.empty
    assert row.iloc[0]["Class"] == "Open"
    assert row.iloc[0]["Age_Group"] == "O25-29"


def test_create_app_builds_layout():
    app = create_app()
    assert app.layout is not None
