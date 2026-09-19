"""Plotting helpers shared by the web app (web.py) and the notebook (notebook.py)."""
import pandas as pd
import plotly.colors as pc

SPLIT_COLS = ['Swim', 'T1', 'Bike', 'T2', 'Run', 'Finish']


def fmt_td(td) -> str:
    """Format a pd.Timedelta as M:SS or H:MM:SS. NaN/NaT -> 'N/A'."""
    if pd.isna(td):
        return 'N/A'
    td = pd.Timedelta(td)
    total_s = int(td.total_seconds())
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'


def rdylgn(v) -> str:
    """RdYlGn colorscale color for a 0-100 percentile value, gray if NaN --
    "green = fast, red = slow", same mapping matplotlib's cm.RdYlGn(v/100)
    gave, via Plotly's own copy of the same colorscale."""
    if pd.isna(v):
        return '#cccccc'
    return pc.sample_colorscale('RdYlGn', max(0.0, min(1.0, v / 100)))[0]


def percentile_bar_kwargs(pct_vals, tlabels, name=None, pattern=None, offsetgroup=None):
    """go.Bar(...) kwargs (minus x/y) for one horizontal percentile-bar panel,
    reversed to match SPLIT_COLS[::-1] axis order -- shared by web.py's
    single/comparison-athlete panels and notebook.py's extended view, all of
    which draw the same "percentile bar + %/time label + RdYlGn color" shape.
    Returns (kwargs, widths); caller supplies x=widths, y=labels_r."""
    pct_r = pct_vals[::-1]
    times_r = tlabels[::-1]
    colors = [rdylgn(v) for v in pct_r]
    widths = [v if pd.notna(v) else 0 for v in pct_r]
    texts = [f'{v:.1f}%  ({t})' if pd.notna(v) else f'N/A  ({t})' for v, t in zip(pct_r, times_r)]
    kwargs = dict(orientation='h', marker_color=colors, text=texts, textposition='outside',
                  cliponaxis=False, hovertemplate='%{y}: %{text}<extra></extra>')
    if name is not None:
        kwargs['name'] = name
    if pattern is not None:
        kwargs['marker_pattern_shape'] = pattern
    if offsetgroup is not None:
        kwargs['offsetgroup'] = offsetgroup
    return kwargs, widths


def add_ref_line(fig, ref_line, **kwargs):
    if ref_line is not None:
        fig.add_vline(x=ref_line, line_dash='dash', line_color='#888888',
                      annotation_text='50th', annotation_position='top', **kwargs)
