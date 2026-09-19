# Refactor notes

Running list of things we'd change if/when we do a bigger pass on this app.
Not a todo list — just decisions and ideas worth remembering, with the
reasoning, so we don't re-litigate them from scratch later. Add to this
whenever a "we should really..." comes up mid-task instead of acting on it
immediately.

## Done

- **Matplotlib → Plotly for every chart the live app renders** (2026-09-20).
  Was: server-side matplotlib render, PNG-encode to base64, ship as
  `html.Img(src=...)`. Fine precomputed once at startup (Age-Group Analysis
  page), a real problem once a chart renders live per-request: the per-race
  Age-Group Breakdown measured ~3s per selection just for `fig.savefig()` on
  two images. Plotly figures ship as a JSON spec and render client-side via
  `dcc.Graph` — measured ~0.2s/figure after warm-up (vs ~1.5s matplotlib),
  plus hover/zoom for free. Converted: `viz/age_groups.py` (`plot_age_groups`,
  `plot_slowest_female`), `viz/web.py` (`plot_single_panel`,
  `plot_comparison`), `viz/notebook.py` (`plot_athlete_extended`).
  `html.Img(src=fig_to_base64(...))` → `dcc.Graph(figure=...)` at every call
  site. Shared bar-panel drawing (RdYlGn percentile color, ref line) moved to
  `viz/__init__.py` since both `web.py` and `notebook.py` need it.
  `data/cache/age_group_content.pkl` had to be regenerated (its content is
  now Plotly Figure objects, not base64 strings — `scripts/prebake_age_group.py`).

  **Deliberately NOT converted**: `viz/notebook.py`'s `plot_athlete()` —
  not imported anywhere in the live app (notebook/interactive use only), no
  performance motivation to touch it. `matplotlib` stays a real dependency
  for this one function; `app.py`'s `matplotlib.use('Agg')` stays too, since
  `notebook.py` still imports `matplotlib.pyplot` at module load time
  regardless of which function you call.

  **Bug found and fixed along the way**: `int(row["Place"])` in three chart
  title-builders (`plot_single_panel`, `plot_athlete_extended`, and
  `plot_athlete`) crashed on an athlete with unknown Place (`pd.NA`) —
  pre-existing in the matplotlib versions too, just never hit before because
  every scraped finisher had a real Place. Surfaced by manually adding a
  personal race result with no known finishing position. Fixed to match the
  `pd.notna(...)` pattern `callbacks.py`'s `_athlete_stat_spans` already used.

## Considered, deliberately deferred

- **Drop Python/Dash from the page entirely** (static JS/React frontend +
  JSON API backend). Raised alongside the Plotly question, but it's a
  different, much larger move — replacing Dash's layout/callback/routing
  system, not just the charting library. The Plotly swap already moves the
  actual slow part (chart rendering) to the browser, which was the real
  motivation. Worth doing later only if there's an independent reason to
  want a different frontend architecture, not as a follow-on to the charting
  fix.
