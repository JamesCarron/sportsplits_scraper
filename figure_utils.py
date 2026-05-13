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
