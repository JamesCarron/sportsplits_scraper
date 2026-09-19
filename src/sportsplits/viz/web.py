import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from sportsplits.viz import SPLIT_COLS, fmt_td, percentile_bar_kwargs as _percentile_bar, add_ref_line as _add_ref_line

_VIEW_META = {
    'class':    ('_pct_class',   'vs Class',      'Percentile  (100 = fastest in class)',      50),
    'overall':  ('_pct_overall', 'vs Whole Race',  'Percentile  (100 = fastest overall)',        50),
    'ag':       ('_pct_ag',      'vs Age Group',   'Percentile  (100 = fastest in age group)',   50),
    'norm':     ('_pct_norm',    'Normalised',     '% of own best split  (100 = strongest discipline)', None),
}


def _lookup(name: str, df: pd.DataFrame):
    hits = df[df['Name'].str.lower() == name.lower()]
    if hits.empty:
        hits = df[df['Name'].str.lower().str.contains(name.lower(), na=False)]
    return hits


def plot_single_panel(name: str, view: str, df: pd.DataFrame):
    """Build a single-panel Plotly figure for one percentile view."""
    hits = _lookup(name, df)
    if hits.empty or len(hits) > 1:
        return None
    row = hits.iloc[0]

    suffix, label, xlabel, ref_line = _VIEW_META[view]

    n_class = int(df[df['Class'] == row['Class']].shape[0])
    n_ag = int(df[(df['Class'] == row['Class']) & (df['Age_Group'] == row['Age_Group'])].shape[0])
    n_all = int(df.shape[0])

    subtitles = {
        'class':   f'vs Class — {row["Class"]}  ({n_class} athletes)',
        'overall': f'vs Whole Race  ({n_all} athletes, all classes)',
        'ag':      f'vs Age Group — {row["Class"]}  ·  {row["Age_Group"]}  ({n_ag} athletes)',
        'norm':    'Normalised — relative to own best split  (100 = strongest discipline)',
    }

    pct_vals = [row.get(f'{s}{suffix}', np.nan) for s in SPLIT_COLS]
    tlabels = [fmt_td(row[s]) for s in SPLIT_COLS]
    labels_r = SPLIT_COLS[::-1]
    place = int(row['Place']) if pd.notna(row['Place']) else '—'

    kwargs, widths = _percentile_bar(pct_vals, tlabels)
    fig = go.Figure(go.Bar(x=widths, y=labels_r, **kwargs))
    _add_ref_line(fig, ref_line)
    fig.update_xaxes(range=[0, 105], title_text=xlabel)
    fig.update_layout(
        title=dict(text=(
            f'{row["Name"]}  ·  {row["Class"]}  ·  {row["Age_Group"]}  ·  '
            f'Finish: {fmt_td(row["Finish"])}  ·  Overall place: {place}'
            f'<br><sup>{subtitles[view]}</sup>'
        )),
        height=450, margin=dict(l=70, r=40),
    )
    return fig


def _fmt_delta(seconds: float) -> str:
    """Format a signed seconds value as +M:SS or -M:SS."""
    sign = '+' if seconds >= 0 else '-'
    total = abs(int(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    t = f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'
    return f'{sign}{t}'


def _header(row) -> str:
    place = int(row['Place']) if pd.notna(row['Place']) else '—'
    return (f'{row["Name"]}  ·  {row["Class"]}  ·  {row["Age_Group"]}  ·  '
            f'Finish: {fmt_td(row["Finish"])}  ·  Place: {place}')


def _time_comparison_figure(row_a, row_b, name_a, name_b):
    s_a = [pd.Timedelta(row_a[c]).total_seconds() if pd.notna(row_a[c]) else 0 for c in SPLIT_COLS]
    s_b = [pd.Timedelta(row_b[c]).total_seconds() if pd.notna(row_b[c]) else 0 for c in SPLIT_COLS]
    text_a = [fmt_td(row_a[c]) for c in SPLIT_COLS]
    text_b = [fmt_td(row_b[c]) for c in SPLIT_COLS]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=s_a, y=SPLIT_COLS, orientation='h', name=name_a, marker_color='#2c7bb6',
                          text=text_a, textposition='outside', cliponaxis=False,
                          hovertemplate='%{y}: %{text}<extra>' + name_a + '</extra>'))
    fig.add_trace(go.Bar(x=s_b, y=SPLIT_COLS, orientation='h', name=name_b, marker_color='#f07030',
                          text=text_b, textposition='outside', cliponaxis=False,
                          hovertemplate='%{y}: %{text}<extra>' + name_b + '</extra>'))
    fig.update_layout(
        title=dict(text=f'{_header(row_a)}<br>{_header(row_b)}', font=dict(size=12)),
        barmode='group', height=480, margin=dict(l=70, r=60),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    fig.update_xaxes(title_text='Seconds')
    return fig


def _percentile_comparison_figure(row_a, row_b, name_a, name_b, view):
    suffix, label, xlabel, ref_line = _VIEW_META[view]

    pct_a = [row_a.get(f'{c}{suffix}', np.nan) for c in SPLIT_COLS]
    pct_b = [row_b.get(f'{c}{suffix}', np.nan) for c in SPLIT_COLS]
    tlabels_a = [fmt_td(row_a[c]) for c in SPLIT_COLS]
    tlabels_b = [fmt_td(row_b[c]) for c in SPLIT_COLS]
    labels_r = SPLIT_COLS[::-1]

    deltas = []
    for col in SPLIT_COLS:
        td_a, td_b = row_a[col], row_b[col]
        if pd.isna(td_a) or pd.isna(td_b):
            deltas.append(np.nan)
        else:
            deltas.append(pd.Timedelta(td_b).total_seconds() - pd.Timedelta(td_a).total_seconds())
    delta_colors = ['#2e8b57' if (pd.notna(d) and d >= 0) else '#c0392b' for d in deltas]
    delta_widths = [d if pd.notna(d) else 0 for d in deltas]
    delta_text = [_fmt_delta(d) if pd.notna(d) else 'N/A' for d in deltas]

    fig = make_subplots(rows=2, cols=1, row_heights=[0.62, 0.38], vertical_spacing=0.16,
                         subplot_titles=[f'Percentile Comparison — {label}', 'Time Delta'])

    kwargs_a, widths_a = _percentile_bar(pct_a, tlabels_a, name=name_a, offsetgroup='a')
    kwargs_b, widths_b = _percentile_bar(pct_b, tlabels_b, name=name_b, pattern='/', offsetgroup='b')
    fig.add_trace(go.Bar(x=widths_a, y=labels_r, **kwargs_a), row=1, col=1)
    fig.add_trace(go.Bar(x=widths_b, y=labels_r, **kwargs_b), row=1, col=1)
    _add_ref_line(fig, ref_line, row=1, col=1)
    fig.update_xaxes(range=[0, 105], title_text=xlabel, row=1, col=1)

    fig.add_trace(go.Bar(x=delta_widths, y=SPLIT_COLS, orientation='h', marker_color=delta_colors,
                          text=delta_text, textposition='outside', cliponaxis=False, showlegend=False,
                          hovertemplate='%{y}: %{text}<extra></extra>'), row=2, col=1)
    fig.add_vline(x=0, line_color='#555555', line_width=1.2, row=2, col=1)
    fig.update_xaxes(title_text=f'← {name_b} faster   |   {name_a} faster →', row=2, col=1)

    fig.update_layout(
        title=dict(text=f'{_header(row_a)}<br>{_header(row_b)}', font=dict(size=12)),
        barmode='group', height=780, margin=dict(l=70, r=60),
        legend=dict(orientation='h', yanchor='bottom', y=1.0, xanchor='right', x=1),
    )
    return fig


def plot_comparison(name_a: str, name_b: str, view: str, df: pd.DataFrame):
    """Build a comparison figure for two athletes."""
    hits_a = _lookup(name_a, df)
    hits_b = _lookup(name_b, df)
    if hits_a.empty or len(hits_a) > 1 or hits_b.empty or len(hits_b) > 1:
        return None

    row_a = hits_a.iloc[0]
    row_b = hits_b.iloc[0]

    if view == 'times':
        return _time_comparison_figure(row_a, row_b, name_a, name_b)
    return _percentile_comparison_figure(row_a, row_b, name_a, name_b, view)
