import io
import base64

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import pandas as pd

SPLIT_COLS = ['Swim', 'T1', 'Bike', 'T2', 'Run', 'Finish']

_VIEW_META = {
    'class':    ('_pct_class',   'vs Class',      'Percentile  (100 = fastest in class)',      50),
    'overall':  ('_pct_overall', 'vs Whole Race',  'Percentile  (100 = fastest overall)',        50),
    'ag':       ('_pct_ag',      'vs Age Group',   'Percentile  (100 = fastest in age group)',   50),
    'norm':     ('_pct_norm',    'Normalised',     '% of own best split  (100 = strongest discipline)', None),
}


def fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('ascii')
    plt.close(fig)
    return f'data:image/png;base64,{encoded}'


def _fmt_td(td) -> str:
    if pd.isna(td):
        return 'N/A'
    td = pd.Timedelta(td)
    total_s = int(td.total_seconds())
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'


def _lookup(name: str, df: pd.DataFrame):
    hits = df[df['Name'].str.lower() == name.lower()]
    if hits.empty:
        hits = df[df['Name'].str.lower().str.contains(name.lower(), na=False)]
    return hits


def _draw_panel(ax, row, splits, pct_vals, tlabels, subtitle, xlabel, ref_line):
    cmap = cm.RdYlGn
    labels_r = splits[::-1]
    pct_r    = pct_vals[::-1]
    times_r  = tlabels[::-1]

    bar_colors = [cmap(v / 100) if pd.notna(v) else '#cccccc' for v in pct_r]
    bar_widths = [v if pd.notna(v) else 0 for v in pct_r]

    bars = ax.barh(labels_r, bar_widths, color=bar_colors, edgecolor='white', height=0.55)

    for bar, pct, tlbl in zip(bars, pct_r, times_r):
        x = pct if pd.notna(pct) else 0
        annotation = f'{pct:.1f}%   ({tlbl})' if pd.notna(pct) else f'N/A   ({tlbl})'
        ax.text(x + 1.5, bar.get_y() + bar.get_height() / 2,
                annotation, va='center', ha='left', fontsize=9)

    if ref_line is not None:
        ax.axvline(ref_line, color='#888888', linestyle='--', linewidth=1, alpha=0.7)
        ax.text(ref_line + 0.8, len(splits) - 0.5, '50th',
                fontsize=8, color='#888888', va='top')

    ax.set_xlim(0, 100)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_title(subtitle, fontsize=10, pad=8, fontweight='semibold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.tick_params(axis='x', labelsize=9)


def plot_single_panel(name: str, view: str, df: pd.DataFrame):
    """Build a single-panel matplotlib figure for one percentile view."""
    hits = _lookup(name, df)
    if hits.empty or len(hits) > 1:
        return None
    row = hits.iloc[0]

    suffix, label, xlabel, ref_line = _VIEW_META[view]

    # Build subtitle with group counts
    n_class = int(df[df['Class'] == row['Class']].shape[0])
    n_ag    = int(df[(df['Class'] == row['Class']) & (df['Age_Group'] == row['Age_Group'])].shape[0])
    n_all   = int(df.shape[0])

    subtitles = {
        'class':   f'vs Class — {row["Class"]}  ({n_class} athletes)',
        'overall': f'vs Whole Race  ({n_all} athletes, all classes)',
        'ag':      f'vs Age Group — {row["Class"]}  ·  {row["Age_Group"]}  ({n_ag} athletes)',
        'norm':    'Normalised — relative to own best split  (100 = strongest discipline)',
    }

    pct_vals = [row.get(f'{s}{suffix}', np.nan) for s in SPLIT_COLS]
    tlabels  = [_fmt_td(row[s]) for s in SPLIT_COLS]

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.suptitle(
        f'{row["Name"]}  ·  {row["Class"]}  ·  {row["Age_Group"]}'
        f'  ·  Finish: {_fmt_td(row["Finish"])}  ·  Overall place: {int(row["Place"])}',
        fontsize=12, fontweight='bold',
    )
    _draw_panel(ax, row, SPLIT_COLS, pct_vals, tlabels, subtitles[view], xlabel, ref_line)
    plt.tight_layout()
    return fig


def _fmt_delta(seconds: float) -> str:
    """Format a signed seconds value as +M:SS or -M:SS."""
    sign = '+' if seconds >= 0 else '-'
    total = abs(int(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    t = f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'
    return f'{sign}{t}'


def _draw_comparison_panel(ax, row_a, row_b, name_a, name_b, suffix, xlabel, ref_line):
    """Grouped horizontal bars: two bars per split (A above, B below), RdYlGn by percentile."""
    cmap = cm.RdYlGn
    n = len(SPLIT_COLS)
    y_positions = np.arange(n)
    bar_h = 0.35

    for i, col in enumerate(SPLIT_COLS):
        val_a = row_a.get(f'{col}{suffix}', np.nan)
        val_b = row_b.get(f'{col}{suffix}', np.nan)
        time_a = _fmt_td(row_a[col])
        time_b = _fmt_td(row_b[col])

        color_a = cmap(val_a / 100) if pd.notna(val_a) else '#cccccc'
        color_b = cmap(val_b / 100) if pd.notna(val_b) else '#cccccc'
        w_a = val_a if pd.notna(val_a) else 0
        w_b = val_b if pd.notna(val_b) else 0

        ax.barh(i + bar_h / 2, w_a, height=bar_h, color=color_a, edgecolor='white')
        ax.barh(i - bar_h / 2, w_b, height=bar_h, color=color_b, edgecolor='#999999',
                hatch='/', linewidth=0.3)

        ann_a = f'{val_a:.1f}%  ({time_a})' if pd.notna(val_a) else f'N/A  ({time_a})'
        ann_b = f'{val_b:.1f}%  ({time_b})' if pd.notna(val_b) else f'N/A  ({time_b})'
        ax.text(w_a + 1, i + bar_h / 2, ann_a, va='center', ha='left', fontsize=8)
        ax.text(w_b + 1, i - bar_h / 2, ann_b, va='center', ha='left', fontsize=8)

    if ref_line is not None:
        ax.axvline(ref_line, color='#888888', linestyle='--', linewidth=1, alpha=0.6)
        ax.text(ref_line + 0.8, n - 0.3, '50th', fontsize=7, color='#888888', va='top')

    # Legend: solid patch for A, hatched patch for B
    import matplotlib.patches as mpatches
    ax.legend(
        handles=[
            mpatches.Patch(facecolor='#4e9a5e', edgecolor='white', label=name_a),
            mpatches.Patch(facecolor='#a0c878', edgecolor='#999999', hatch='/', label=name_b),
        ],
        loc='lower right', fontsize=8, framealpha=0.7,
    )

    ax.set_yticks(y_positions)
    ax.set_yticklabels(SPLIT_COLS)
    ax.set_xlim(0, 100)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.tick_params(axis='x', labelsize=9)


def _draw_delta_panel(ax, row_a, row_b, name_a, name_b):
    """Single bar per split: B_time - A_time in seconds. Green = A faster, Red = B faster."""
    deltas = []
    for col in SPLIT_COLS:
        td_a = row_a[col]
        td_b = row_b[col]
        if pd.isna(td_a) or pd.isna(td_b):
            deltas.append(np.nan)
        else:
            deltas.append(pd.Timedelta(td_b).total_seconds() - pd.Timedelta(td_a).total_seconds())

    n = len(SPLIT_COLS)
    colors = ['#2e8b57' if (pd.notna(d) and d >= 0) else '#c0392b' for d in deltas]
    widths = [d if pd.notna(d) else 0 for d in deltas]

    bars = ax.barh(SPLIT_COLS, widths, color=colors, edgecolor='white', height=0.5)

    for bar, d in zip(bars, deltas):
        if pd.isna(d):
            continue
        x = d
        ha = 'left' if d >= 0 else 'right'
        offset = 0.5 if d >= 0 else -0.5
        ax.text(x + offset, bar.get_y() + bar.get_height() / 2,
                _fmt_delta(d), va='center', ha=ha, fontsize=8)

    ax.axvline(0, color='#555555', linewidth=1.2)
    ax.set_xlabel(f'← {name_b} faster   |   {name_a} faster →', fontsize=9)
    ax.set_title('Time Delta', fontsize=10, pad=8, fontweight='semibold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.tick_params(axis='x', labelsize=9)


def _draw_time_comparison_panel(ax, row_a, row_b, name_a, name_b):
    """Grouped horizontal bars showing raw split times in seconds."""
    n = len(SPLIT_COLS)
    y_positions = np.arange(n)
    bar_h = 0.35
    color_a = '#2c7bb6'
    color_b = '#f07030'

    for i, col in enumerate(SPLIT_COLS):
        td_a = row_a[col]
        td_b = row_b[col]
        s_a = pd.Timedelta(td_a).total_seconds() if pd.notna(td_a) else 0
        s_b = pd.Timedelta(td_b).total_seconds() if pd.notna(td_b) else 0

        ax.barh(i + bar_h / 2, s_a, height=bar_h, color=color_a, edgecolor='white')
        ax.barh(i - bar_h / 2, s_b, height=bar_h, color=color_b, edgecolor='white')

        ax.text(s_a + 2, i + bar_h / 2, _fmt_td(td_a), va='center', ha='left', fontsize=8)
        ax.text(s_b + 2, i - bar_h / 2, _fmt_td(td_b), va='center', ha='left', fontsize=8)

    import matplotlib.patches as mpatches
    ax.legend(
        handles=[mpatches.Patch(color=color_a, label=name_a),
                 mpatches.Patch(color=color_b, label=name_b)],
        loc='lower right', fontsize=8, framealpha=0.7,
    )

    ax.set_yticks(y_positions)
    ax.set_yticklabels(SPLIT_COLS)
    ax.set_title('Split Times', fontsize=10, pad=8, fontweight='semibold')
    ax.set_xlabel('Seconds', fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.tick_params(axis='x', labelsize=9)


import warnings as _warnings


def plot_comparison(name_a: str, name_b: str, view: str, df: pd.DataFrame):
    """Build a comparison figure for two athletes."""
    hits_a = _lookup(name_a, df)
    hits_b = _lookup(name_b, df)
    if hits_a.empty or len(hits_a) > 1 or hits_b.empty or len(hits_b) > 1:
        return None

    row_a = hits_a.iloc[0]
    row_b = hits_b.iloc[0]

    def _header(row):
        place = int(row['Place']) if pd.notna(row['Place']) else '—'
        return f'{row["Name"]}  ·  {row["Class"]}  ·  {row["Age_Group"]}  ·  Finish: {_fmt_td(row["Finish"])}  ·  Place: {place}'

    with _warnings.catch_warnings():
        _warnings.simplefilter('ignore', UserWarning)

        if view == 'times':
            fig, ax = plt.subplots(figsize=(12, 5))
            fig.suptitle(f'{_header(row_a)}\n{_header(row_b)}', fontsize=10, fontweight='bold')
            _draw_time_comparison_panel(ax, row_a, row_b, name_a, name_b)
            plt.tight_layout()
            return fig

        suffix, label, xlabel, ref_line = _VIEW_META[view]
        fig, (ax_pct, ax_delta) = plt.subplots(
            2, 1, figsize=(12, 9), gridspec_kw={'hspace': 0.55}
        )
        fig.suptitle(f'{_header(row_a)}\n{_header(row_b)}', fontsize=10, fontweight='bold')
        ax_pct.set_title(f'Percentile Comparison — {label}', fontsize=10, pad=8, fontweight='semibold')
        _draw_comparison_panel(ax_pct, row_a, row_b, name_a, name_b, suffix, xlabel, ref_line)
        _draw_delta_panel(ax_delta, row_a, row_b, name_a, name_b)
        plt.tight_layout()
        return fig


def build_summary_fig(df: pd.DataFrame):
    """Horizontal bar chart of median split times by class."""
    splits = ['Swim', 'T1', 'Bike', 'T2', 'Run']
    classes = df['Class'].dropna().unique()

    fig, axes = plt.subplots(1, len(splits), figsize=(14, max(3, len(classes) * 0.8 + 1)),
                             sharey=True)
    fig.suptitle('Median Split Times by Class', fontsize=12, fontweight='bold')

    colors = plt.cm.Set2.colors

    for ax, split in zip(axes, splits):
        medians = (
            df.groupby('Class')[split]
              .median()
              .dropna()
              .sort_values()
        )
        bar_labels = [_fmt_td(v) for v in medians.values]
        bars = ax.barh(medians.index.tolist(), medians.dt.total_seconds(),
                       color=colors[:len(medians)], edgecolor='white', height=0.5)
        for bar, lbl in zip(bars, bar_labels):
            ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                    lbl, va='center', ha='left', fontsize=8)
        ax.set_title(split, fontsize=10, fontweight='semibold')
        ax.set_xlabel('seconds', fontsize=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(axis='y', length=0)
        ax.tick_params(axis='x', labelsize=8)

    plt.tight_layout()
    return fig
