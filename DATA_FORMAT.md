# Parsed Output Data Format

## Source

Plain-text race results file (`Clonmel.txt`). The first line is a header and is skipped. Each subsequent line represents one athlete's result.

## Raw Parse Output

Produced by `parse_input.load_results()`. One row per athlete.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `Place` | `int` | No | Overall finishing position |
| `Bib` | `int` | No | Race bib number |
| `Name` | `str` | No | Athlete full name |
| `Age_Group` | `str` | Yes | Age band, e.g. `From 30 to 34`, `OverAll`, `TBC`, `Relay Team` |
| `Group_Rank` | `int` | Yes | Finishing rank within the athlete's age group. `None` for some Female entries and relay teams |
| `Class` | `str` | No | `Open`, `Female`, or `RELAY` |
| `Club` | `str` | Yes | Athlete's club or team name. Empty string if not listed |
| `Swim` | `pd.Timedelta` | Yes | Swim split time |
| `T1` | `pd.Timedelta` | Yes | Transition 1 time |
| `Bike` | `pd.Timedelta` | Yes | Bike split time |
| `T2` | `pd.Timedelta` | Yes | Transition 2 time |
| `Run` | `pd.Timedelta` | Yes | Run split time |
| `Finish` | `pd.Timedelta` | Yes | Total race finish time |

### Time Format

Times in the source file are strings in one of two formats:

- `M:SS` — e.g. `45:30` (minutes and seconds)
- `H:MM:SS` — e.g. `1:23:45` (hours, minutes, seconds)

After parsing, all time values are stored as `pd.Timedelta`. `pd.NaT` is used where a split was not recorded (e.g. DNF entries).

### Partial Records

Some entries do not have a full set of six splits:

- **DNF / incomplete**: only the finish time is recorded; all split columns are `pd.NaT`
- **Lines with fewer than 6 times**: split columns are filled in order and remaining are `pd.NaT`

---

## Metrics Output

Produced by `metrics.build_metrics()` (or by calling the individual `add_*` functions in sequence). Adds 24 columns to the raw parse output.

### Percentile Convention

All percentile values are in the range `0–100` where **100 = fastest** in the group and **0 = slowest**. `pd.NaT` split times are excluded from ranking and their percentile is `NaN`.

### Class Percentiles — `add_percentiles()`

Rank within the athlete's `Class` (`Open` vs `Female` separately).

| Column pattern | Example | Grouping |
|---|---|---|
| `{split}_pct_class` | `Swim_pct_class` | All athletes with the same `Class` |
| `{split}_pct_ag` | `Swim_pct_ag` | Athletes with the same `Class` **and** `Age_Group` |

Splits: `Swim`, `T1`, `Bike`, `T2`, `Run`, `Finish` → **12 columns total**.

### Overall Percentiles — `add_overall_percentiles()`

Rank across the entire field regardless of class.

| Column pattern | Example | Grouping |
|---|---|---|
| `{split}_pct_overall` | `Swim_pct_overall` | All athletes in the race |

→ **6 columns total**.

### Normalised Percentiles — `add_normalised_percentiles(base='pct_class')`

Each split percentile expressed as a fraction of the athlete's own best split percentile. Shows relative strengths and weaknesses independent of overall ability.

| Column pattern | Example | Formula |
|---|---|---|
| `{split}_pct_norm` | `Swim_pct_norm` | `split_pct / max(all_split_pcts) * 100` |

- **100** = this split is the athlete's strongest discipline
- **< 100** = this split is weaker relative to the athlete's own ceiling
- The `base` parameter controls which percentile family is used as the denominator (`pct_class`, `pct_ag`, or `pct_overall`)

→ **6 columns total**.

### Full Column List (36 total)

```
Place, Bib, Name, Age_Group, Group_Rank, Class, Club,
Swim, T1, Bike, T2, Run, Finish,
Swim_pct_class,   T1_pct_class,   Bike_pct_class,   T2_pct_class,   Run_pct_class,   Finish_pct_class,
Swim_pct_ag,      T1_pct_ag,      Bike_pct_ag,      T2_pct_ag,      Run_pct_ag,      Finish_pct_ag,
Swim_pct_overall, T1_pct_overall, Bike_pct_overall, T2_pct_overall, Run_pct_overall, Finish_pct_overall,
Swim_pct_norm,    T1_pct_norm,    Bike_pct_norm,    T2_pct_norm,    Run_pct_norm,    Finish_pct_norm
```
