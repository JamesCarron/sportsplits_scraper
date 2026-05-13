from parse_input import load_results as _load_clonmel
from parse_lost_sheep import load_results as _load_lost_sheep
from metrics import build_metrics_from_df

# Registry: display name → (file path, loader function)
# Add new races here — loader must return a DataFrame in the standard 13-column format.
REGISTRY = {
    'Clonmel 2024':     ('Clonmel.txt',                    _load_clonmel),
    'Lost Sheep 2025':  ('lost_sheep_2025_results.csv',    _load_lost_sheep),
}


def load_all() -> dict:
    """Load and compute metrics for every registered race. Returns {name: df}."""
    result = {}
    for name, (path, loader) in REGISTRY.items():
        raw = loader(path)
        result[name] = build_metrics_from_df(raw)
    return result
