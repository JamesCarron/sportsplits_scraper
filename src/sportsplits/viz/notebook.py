import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from sportsplits.viz import SPLIT_COLS, fmt_td, percentile_bar_kwargs, add_ref_line

plt.rcParams['figure.dpi'] = 150


def plot_athlete(name: str, df: pd.DataFrame) -> None:
    """Visualise one athlete's split times and percentile rankings."""
    hits = df[df['Name'].str.lower() == name.lower()]
    if hits.empty:
        hits = df[df['Name'].str.lower().str.contains(name.lower(), na=False)]
    if hits.empty:
        print(f'No athlete found matching "{name}"')
        return
    if len(hits) > 1:
        print('Multiple matches — be more specific:')
        print(hits[['Name', 'Class', 'Age_Group']].to_string(index=False))
        return

    row = hits.iloc[0]

    splits    = SPLIT_COLS
    pct_class = [row.get(f'{s}_pct_class', np.nan) for s in splits]
    pct_ag    = [row.get(f'{s}_pct_ag',    np.nan) for s in splits]
    tlabels   = [fmt_td(row[s]) for s in splits]

    cmap = cm.RdYlGn

    fig, (ax_class, ax_ag) = plt.subplots(
        2, 1, figsize=(12, 9),
        gridspec_kw={'hspace': 0.55}
    )

    place = int(row['Place']) if pd.notna(row['Place']) else '—'
    fig.suptitle(
        f'{row["Name"]}  ·  {row["Class"]}  ·  {row["Age_Group"]}'
        f'  ·  Finish: {fmt_td(row["Finish"])}  ·  Overall place: {place}',
        fontsize=13, fontweight='bold', y=1.02
    )

    def _draw(ax, pct_vals, subtitle):
        labels_r = splits[::-1]
        pct_r    = pct_vals[::-1]
        times_r  = tlabels[::-1]

        bar_colors = [
            cmap(v / 100) if pd.notna(v) else '#cccccc'
            for v in pct_r
        ]
        bar_widths = [v if pd.notna(v) else 0 for v in pct_r]

        bars = ax.barh(labels_r, bar_widths, color=bar_colors,
                       edgecolor='white', height=0.55)

        for bar, pct, tlbl in zip(bars, pct_r, times_r):
            x = pct if pd.notna(pct) else 0
            annotation = f'{pct:.1f}%   ({tlbl})' if pd.notna(pct) else f'N/A   ({tlbl})'
            ax.text(
                x + 1.5,
                bar.get_y() + bar.get_height() / 2,
                annotation,
                va='center', ha='left', fontsize=10
            )

        ax.axvline(50, color='#888888', linestyle='--', linewidth=1, alpha=0.7)
        ax.text(50.8, len(splits) - 0.5, '50th', fontsize=8,
                color='#888888', va='top')

        ax.set_xlim(0, 100)
        ax.set_xlabel('Percentile  (100 = fastest in group)', fontsize=10)
        ax.set_title(subtitle, fontsize=11, pad=10, fontweight='semibold')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(axis='y', length=0)
        ax.tick_params(axis='x', labelsize=9)

    _draw(
        ax_class, pct_class,
        f'vs Class — {row["Class"]}  ({int(df[df["Class"] == row["Class"]]["Class"].count())} athletes)'
    )
    _draw(
        ax_ag, pct_ag,
        f'vs Age Group — {row["Class"]}  ·  {row["Age_Group"]}'
        f'  ({int(df[(df["Class"] == row["Class"]) & (df["Age_Group"] == row["Age_Group"])].shape[0])} athletes)'
    )

    return fig


def plot_athlete_extended(name: str, df: pd.DataFrame):
    """
    Four-panel view of one athlete's splits:
      1. vs Class          — pct_class (same as plot_athlete top panel)
      2. vs Whole Race     — pct_overall (all classes combined)
      3. vs Age Group      — pct_ag
      4. Normalised        — each split as % of athlete's own best split
                             (100 = their strongest discipline, lower = relative weakness)

    Plotly, not matplotlib -- renders via dcc.Graph in the live app (see
    docs/REFACTOR_NOTES.md); this is the one place that still prints and
    returns None on a no/ambiguous-match instead of returning None for the
    caller to handle, since it's also used directly from a notebook.
    """
    hits = df[df['Name'].str.lower() == name.lower()]
    if hits.empty:
        hits = df[df['Name'].str.lower().str.contains(name.lower(), na=False)]
    if hits.empty:
        print(f'No athlete found matching "{name}"')
        return None
    if len(hits) > 1:
        print('Multiple matches — be more specific:')
        print(hits[['Name', 'Class', 'Age_Group']].to_string(index=False))
        return None

    row = hits.iloc[0]
    splits = SPLIT_COLS
    tlabels = [fmt_td(row[s]) for s in splits]
    labels_r = splits[::-1]

    n_class = int(df[df['Class'] == row['Class']].shape[0])
    n_ag = int(df[(df['Class'] == row['Class']) & (df['Age_Group'] == row['Age_Group'])].shape[0])
    n_overall = int(df.shape[0])

    panels = [
        (
            [row.get(f'{s}_pct_class', np.nan) for s in splits],
            f'vs Class — {row["Class"]}  ({n_class} athletes)',
            'Percentile  (100 = fastest in class)',
            50,
        ),
        (
            [row.get(f'{s}_pct_overall', np.nan) for s in splits],
            f'vs Whole Race  ({n_overall} athletes, all classes)',
            'Percentile  (100 = fastest overall)',
            50,
        ),
        (
            [row.get(f'{s}_pct_ag', np.nan) for s in splits],
            f'vs Age Group — {row["Class"]}  ·  {row["Age_Group"]}  ({n_ag} athletes)',
            'Percentile  (100 = fastest in age group)',
            50,
        ),
        (
            [row.get(f'{s}_pct_norm', np.nan) for s in splits],
            'Normalised — relative to own best split  (100 = strongest discipline)',
            '% of own best split percentile',
            None,
        ),
    ]

    fig = make_subplots(rows=4, cols=1, vertical_spacing=0.08,
                         subplot_titles=[subtitle for _, subtitle, _, _ in panels])

    for i, (pct_vals, subtitle, xlabel, ref_line) in enumerate(panels, start=1):
        kwargs, widths = percentile_bar_kwargs(pct_vals, tlabels)
        fig.add_trace(go.Bar(x=widths, y=labels_r, **kwargs), row=i, col=1)
        add_ref_line(fig, ref_line, row=i, col=1)
        fig.update_xaxes(range=[0, 105], title_text=xlabel, row=i, col=1)

    place = int(row['Place']) if pd.notna(row['Place']) else '—'
    fig.update_layout(
        title=dict(text=(
            f'{row["Name"]}  ·  {row["Class"]}  ·  {row["Age_Group"]}  ·  '
            f'Finish: {fmt_td(row["Finish"])}  ·  Overall place: {place}'
        )),
        height=1400, margin=dict(l=70, r=40), showlegend=False,
    )
    return fig


if __name__ == '__main__':
    from sportsplits.races import load_all
    df = next(iter(load_all().values()))
    name = df['Name'].iloc[0]
    plot_athlete(name, df)
    plot_athlete_extended(name, df)
