# Web Interface Architecture (Dash analytics app)

A reusable blueprint for a small-to-mid data-analysis web app: load some datasets,
compute derived metrics, and let a user explore/compare records with server-rendered
charts — plus add new data sources at runtime from the UI. This document describes the
patterns used in this project (`sportsplits`) in a project-agnostic way so they can be
lifted into other apps.

## When this architecture fits

- Single-user or small-team internal tool, run locally or on one host.
- Data volume fits comfortably in memory (tens of thousands of rows per dataset).
- You want rich, publication-quality charts without writing front-end JavaScript.
- You value a short path from "pandas DataFrame" to "interactive web page".

It is **not** aimed at high-concurrency public sites or anything needing per-user
sessions/auth — the app holds one shared in-memory dataset (see Trade-offs).

## Tech stack

| Concern            | Choice                                   | Why |
|--------------------|------------------------------------------|-----|
| Web framework      | **Dash** (Flask + React under the hood)  | Declarative layout in pure Python; reactive callbacks; no JS required. |
| Data               | **pandas**                               | Everything is a DataFrame in the standard schema. |
| Charts             | **matplotlib** (Agg backend) → PNG       | Server-render figures, ship them as base64 `<img>`; full styling control. |
| Packaging          | **src layout** + `pyproject.toml`        | Clean import root; optional editable install. |
| Launch             | `run.py` / `.bat` (no install required)  | Bootstraps `src/` onto `sys.path` then starts the server. |

## Directory layout

```
src/<package>/
  app.py         # create_app() factory + main()  — composition root
  config.py      # centralized filesystem paths (anchored to the package, not CWD)
  layout.py      # make_layout(names) -> Dash component tree (pure structure, has IDs)
  callbacks.py   # register_callbacks(app, state) -> wires interactivity
  metrics.py     # pure functions that add derived columns to a DataFrame
  races.py       # DATA REGISTRY + load_all() + runtime add
  viz/           # rendering: web.py (app figures) returns matplotlib Figures
  assets/        # style.css — Dash auto-serves this folder (must sit beside app.py)
  parsers/       # data-source adapters (one module per source family)
data/            # inputs/outputs, separate from code
run.py           # `python run.py` — no-install launcher
```

The four layers — **layout** (what the page is), **callbacks** (how it reacts),
**viz** (how data becomes pixels), **data** (where records come from) — never import
"downward" in a cycle: `callbacks` depends on `layout`, `viz`, and the data layer; the
data layer knows nothing about the UI.

## Core patterns

### 1. App factory (composition root)

`create_app()` is the single place the whole app is assembled: load data → build layout
→ register callbacks. This keeps import side-effects out of module top level, makes tests
able to spin up a fresh app, and gives the launcher a clean entry point.

```python
def create_app() -> dash.Dash:
    state = load_all()                       # {name: DataFrame}, computed once
    app = dash.Dash(__name__, title='...')   # __name__ => assets/ resolved beside this file
    app.layout = make_layout(list(state))
    register_callbacks(app, state)           # state handed to callbacks via closure
    return app

def main() -> None:
    create_app().run(debug=False, port=8050)
```

### 2. Config-anchored paths (run from anywhere)

Never resolve data paths relative to the current working directory. Anchor them to a
known file so the app behaves identically whether launched from the repo root, a `.bat`,
or an IDE.

```python
# config.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]   # config.py -> pkg -> src -> root
DATA_DIR = PROJECT_ROOT / "data"
```

### 3. Data registry + loader

Every dataset is one entry in a dict: display name → `(path, loader_fn)`. Loaders all
return the **same standard schema** (a DataFrame with a fixed column set), so the rest of
the app is source-agnostic. Adding a source = adding a registry entry.

```python
REGISTRY = {
    'Dataset A': (path_a, load_csv_a),
    'Dataset B': (path_b, load_api_b),
}

def load_all() -> dict:
    return {name: build_metrics(loader(path)) for name, (path, loader) in REGISTRY.items()}
```

Where the registry can be **generated** from a config/spec list (rather than hand-written),
do that — it removes duplication and guarantees a name is registered exactly once.

### 4. Compute derived data on load, don't persist it

Raw/standard data is stored; **derived** columns (percentiles, ranks, normalizations) are
recomputed at load by pure functions in `metrics.py`. They never live in the CSVs, so they
can't go stale and the on-disk format stays simple.

```python
df = build_metrics(load_processed(path))   # adds ~24 derived columns
```

### 5. In-memory state passed to callbacks by closure

`load_all()` produces a `{name: DataFrame}` dict once at startup. It is handed to
`register_callbacks(app, state)`, and every callback closes over `state`. This is fast
(no re-reads) and makes runtime mutation trivial (pattern 9).

### 6. Server-rendered matplotlib → base64 PNG

Instead of a JS charting library, figures are built with matplotlib on the **Agg** backend
and shipped to the browser as a base64-encoded PNG inside an `<img>`. The callback returns
the data-URI string into `Img.src`.

```python
import matplotlib
matplotlib.use('Agg')          # MUST run before any pyplot import (headless render)

def fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    buf.seek(0)
    data = base64.b64encode(buf.read()).decode('ascii')
    plt.close(fig)             # ALWAYS close — otherwise figures leak and memory grows
    return f'data:image/png;base64,{data}'
```

Layout side: `html.Img(id='chart')`; callback side: `return fig_to_base64(fig)`. Wrap the
image in `dcc.Loading(...)` so the user sees a spinner while the server renders.

- **Pros:** total control over styling; identical output everywhere; reuse the same plot
  functions in notebooks; no front-end build step.
- **Cons:** charts are static images (no hover/zoom); every interaction is a server
  round-trip + re-render. Fine for this scale; see Trade-offs.

### 7. Layout vs callbacks separation

`layout.py` is **pure structure** — it returns a component tree and assigns `id`s, but
contains no behavior. `callbacks.py` references those ids. Small pure helpers that build
repeated fragments (KPI cards, stat rows) live next to the layout and are imported by
callbacks when they need to regenerate a fragment. This keeps the page definition readable
and the behavior in one place.

### 8. Callback conventions

- **One owner per output property.** Two callbacks cannot both write the same
  `component.property`. If two triggers must update the same output, **merge them into one
  callback** with multiple `Input`s and branch on `ctx.triggered_id`:

  ```python
  @app.callback(Output('sel', 'options'), Output('sel', 'value'), Output('status', 'children'),
                Input('add-btn', 'n_clicks'), Input('search-add-btn', 'n_clicks'),
                State(...), prevent_initial_call=True)
  def add(manual, from_search, ...):
      if ctx.triggered_id == 'search-add-btn': ...
      else: ...
  ```

- **`Input` vs `State`:** `Input` triggers the callback; `State` is read-only context. Put
  the button click as `Input`, the form field values as `State`.
- **`no_update`** to leave an output untouched (e.g. show an error without resetting the
  dropdown).
- **`prevent_initial_call=True`** for actions that must not fire on page load.
- **`dcc.Loading`** around any output produced by a slow (I/O or render) callback.
- Text you insert into the DOM is escaped by Dash — safe by default.

### 9. Runtime additions with persistence

New data sources can be added from the UI without a restart, and survive one:

1. A callback validates input and calls an `add_*` service in the data layer.
2. The service fetches/derives the dataset, writes it to `data/`, **appends a spec to a
   JSON file** (`data/user_events.json`) so it's remembered, and updates the in-memory
   `REGISTRY` + the live `state` dict.
3. The callback rebuilds the selector's `options` from `state` and selects the new item.

On next startup the registry is built from *built-in specs + persisted specs*, so the
addition is permanent. Guard against duplicate names against the live `state`.

### 10. Assets & styling

Dash auto-serves any file in a folder named `assets/` located **next to the module that
constructs `Dash(__name__)`**. In a src-layout package that means `src/<package>/assets/`.
Keep it there; a single `style.css` with semantic class names is enough — no bundler.

### 11. Run without installing

A src layout normally wants `pip install -e .`. To avoid forcing that, a top-level
launcher puts `src/` on the path and starts the server; a `conftest.py` does the same for
tests; a notebook does it in its first cell. `pyproject.toml` still allows an editable
install for anyone who wants the console entry point.

```python
# run.py
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from <package>.app import main
main()
```

## Request lifecycle (one interaction)

```
user changes a control
        │  (browser sends changed prop to Dash)
        ▼
@app.callback fires  ──reads──▶  in-memory state dict (DataFrames)
        │                              │
        │                       metrics already computed at load
        ▼                              ▼
build matplotlib Figure  ──▶  fig_to_base64 (PNG data-URI)
        │
        ▼
returned into Img.src / children  ──▶  browser swaps the image
```

## Trade-offs & scaling notes

- **Shared in-memory state:** one process holds one `state` dict for all users. Great for
  a local/internal tool; for multi-user you'd move state to a cache/db and make callbacks
  stateless. Runtime `add_*` mutating a shared dict is not safe across multiple worker
  processes — run a single worker, or persist + reload.
- **Static charts:** server-render is simple and pixel-perfect but not interactive. If you
  need hover/zoom/cross-filter, swap `viz` for a client library (Plotly via
  `dcc.Graph`) — the rest of the architecture (registry, metrics, callbacks) is unchanged.
- **Blocking work in callbacks:** network scrapes/heavy renders run synchronously. Keep
  them behind `dcc.Loading`; for anything long, use Dash background callbacks or a queue.
- **`debug=False`** in production-ish use; set `True` only while developing (hot reload +
  in-browser tracebacks).

## Reuse checklist

1. Pick your **standard schema** (the columns every loader must produce).
2. Write `config.py` path anchors and a `data/` dir.
3. Implement one **loader per source**; register them in `REGISTRY` (or generate it).
4. Put derived calculations in pure `metrics` functions applied at load.
5. Build `layout.py` (structure + ids) and `viz` (functions returning Figures).
6. Wire `callbacks.py`: one owner per output, `ctx.triggered_id` to merge, `dcc.Loading`
   on slow outputs.
7. Add the `create_app()`/`main()` factory, `run.py`, and a launcher script.
8. (Optional) Runtime add + JSON persistence for user-supplied sources.
