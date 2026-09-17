# Sportsplits — Triathlon Results Analyser

A Dash web app for exploring triathlon split times and percentile rankings, plus a
two-stage pipeline that scrapes results from [my.raceresult.com](https://my.raceresult.com)
and turns them into the app's standard format.

## Run the app

No install required:

```bash
python run.py
```

Then open <http://localhost:8050>. (Optionally `pip install -e .` to get a
`sportsplits` console command and editable installs.)

## Project layout

```
src/sportsplits/        application package
  app.py                Dash app factory (create_app / main)
  layout.py callbacks.py  UI + interactivity
  metrics.py            percentile / normalised metric columns
  races.py              REGISTRY of races the app loads
  config.py             central data paths
  viz/                  plotting (web.py = app charts, notebook.py = notebook charts)
  parsers/              clonmel.py, lost_sheep.py, raceresult/{common,events}.py
data/
  raw/                  source as obtained (RaceResult API dumps + file inputs)
  processed/            generated, app-ready standard-format CSVs
docs/DATA_FORMAT.md     data format + pipeline reference
scrape_and_process.ipynb  refresh the RaceResult data
```

## Refresh / add RaceResult data

The pipeline is two clearly separated stages (see `parsers/raceresult/common.py`):

1. **Scrape** → dump each event's lists to raw CSVs in `data/raw/` with no interpretation.
2. **Process** → map the raw CSVs to the standard 13-column CSVs in `data/processed/`.

Both stages overwrite their outputs, so re-pulling never duplicates rows. Open
`scrape_and_process.ipynb` and run it to refresh every event.

### Add a race from the web app

In the running app, expand **"➕ Add a race from my.raceresult.com"** under the race
selector. Two ways to add:

- **Search** the public event directory by name — results list each event's name, date,
  type and location. Pick one and click **Add selected race**.
- **Paste a results URL** (or bare event id) plus a display name and click **Add**.

Either way the app auto-detects the event's column layout, scrapes and processes it, and
selects it immediately. Added races are persisted to `data/user_events.json`, so they
survive a restart. Auto-detection targets the standard triathlon layout; unusual
multi-contest events may still need a hand-tuned spec.

### Add a built-in race in code

Append an `EventSpec` to `src/sportsplits/parsers/raceresult/events.py` (`BUILTIN_EVENTS`)
and re-run the notebook — `races.py` builds its `REGISTRY` straight from `all_events()`,
so the app picks it up automatically.

## Ironman World Championship races

The race selector's **Collection** dropdown separates the full-distance Ironman World
Championship and Ironman 70.3 World Championship races (2016–2025) from your own races.
Unlike RaceResult, these aren't auto-scraped — see
[docs/DATA_FORMAT.md](docs/DATA_FORMAT.md#ironman-world-championship-races--manual-fetch-then-process)
for why, and how to add another race id to
`src/sportsplits/parsers/ironman/events.py`.

The app's metric columns are computed at load time (`metrics.build_metrics_from_df`), so they
are never baked into the CSVs and can't go stale.

## Tests

```bash
pytest
```
