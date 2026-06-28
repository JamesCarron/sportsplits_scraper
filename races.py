from race_results.parsers.parse_clonmel_draft import load_results as _load_clonmel_draft
from race_results.parsers.parse_clonmel_camida_2026 import load_results as _load_clonmel_2026
from race_results.parsers.parse_lost_sheep_2025 import load_results as _load_lost_sheep
from race_results.parsers.parse_raceresult_402195 import load_results_csv as _load_fastnet_2026
from race_results.parsers.parse_raceresult_343797 import load_results_csv as _load_fastnet_2025
from race_results.parsers.parse_raceresult_403737 import load_results_csv as _load_jailbreak_2026
from metrics import build_metrics_from_df

# Registry: display name → (file path, loader function)
# Add new races here — loader must return a DataFrame in the standard 13-column format.
REGISTRY = {
    'Clonmel 2026_DRAFT': ('race_results/Clonmel_Camida_2026_DRAFT.txt', _load_clonmel_draft),
    'Clonmel 2026':       ('race_results/Clonmel_Camida_2026.txt',        _load_clonmel_2026),
    'Lost Sheep 2025':    ('race_results/CTC_Lost_Sheep_2025.csv',         _load_lost_sheep),
    'Fastnet Sprint 2026': ('race_results/Fastnet_Sprint_Triathlon_2026.csv', _load_fastnet_2026),
    'Fastnet Sprint 2025': ('race_results/Fastnet_Sprint_Triathlon_2025.csv', _load_fastnet_2025),
    'Jailbreak 2026':      ('race_results/Jailbreak_2026.csv',                _load_jailbreak_2026),
}


def load_all() -> dict:
    """Load and compute metrics for every registered race. Returns {name: df}."""
    result = {}
    for name, (path, loader) in REGISTRY.items():
        raw = loader(path)
        result[name] = build_metrics_from_df(raw)
    return result
