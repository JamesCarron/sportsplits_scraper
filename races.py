from race_results.parsers.parse_clonmel_draft import load_results as _load_clonmel_draft
from race_results.parsers.parse_clonmel_camida_2026 import load_results as _load_clonmel_2026
from race_results.parsers.parse_lost_sheep_2025 import load_results as _load_lost_sheep
from metrics import build_metrics_from_df

# Registry: display name → (file path, loader function)
# Add new races here — loader must return a DataFrame in the standard 13-column format.
REGISTRY = {
    'Clonmel 2026_DRAFT': ('race_results/Clonmel_Camida_2026_DRAFT.txt', _load_clonmel_draft),
    'Clonmel 2026':       ('race_results/Clonmel_Camida_2026.txt',        _load_clonmel_2026),
    'Lost Sheep 2025':    ('race_results/CTC_Lost_Sheep_2025.csv',         _load_lost_sheep),
}


def load_all() -> dict:
    """Load and compute metrics for every registered race. Returns {name: df}."""
    result = {}
    for name, (path, loader) in REGISTRY.items():
        raw = loader(path)
        result[name] = build_metrics_from_df(raw)
    return result
