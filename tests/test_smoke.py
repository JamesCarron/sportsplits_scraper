"""End-to-end smoke tests for the restructured package.

These read the committed processed CSVs in data/processed/ (no network), so they
exercise the full registry -> loader -> metrics path and the Dash app factory.
"""
from sportsplits.app import create_app
from sportsplits.races import REGISTRY, load_all


def test_load_all_returns_every_race_with_metrics():
    dfs = load_all()
    assert set(dfs) == set(REGISTRY)
    assert len(dfs) == 35
    for name, df in dfs.items():
        assert len(df) > 0, f"{name} loaded no rows"
        assert df.shape[1] == 37, f"{name} has {df.shape[1]} columns, expected 37"


def test_identity_swap_applied():
    """The known Fastnet 2026 identity mix-up is corrected in the processed data."""
    row = load_all()["Fastnet Sprint 2026"].query("Name == 'James Carron'")
    assert not row.empty
    assert row.iloc[0]["Class"] == "Open"
    assert row.iloc[0]["Age_Group"] == "O25-29"


def test_create_app_builds_layout():
    app = create_app()
    assert app.layout is not None
