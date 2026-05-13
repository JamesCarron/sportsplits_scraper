import pandas as pd
from dash import dcc, html
from figure_utils import _fmt_td

SPLIT_COLS = ['Swim', 'T1', 'Bike', 'T2', 'Run', 'Finish']


def _kpi_card(label: str, value: str) -> html.Div:
    return html.Div(className='kpi-card', children=[
        html.Div(value, className='kpi-value'),
        html.Div(label, className='kpi-label'),
    ])


def _build_summary_stats(df: pd.DataFrame) -> list:
    total = len(df)
    class_counts = df['Class'].value_counts().to_dict()

    fastest_row = df.loc[df['Finish'].idxmin()]
    fastest_str = f'{fastest_row["Name"]} ({_fmt_td(fastest_row["Finish"])})'

    return [
        _kpi_card('Total Finishers', str(total)),
        _kpi_card('Open', str(class_counts.get('Open', 0))),
        _kpi_card('Female', str(class_counts.get('Female', 0))),
        _kpi_card('Fastest Finisher', fastest_str),
    ]


def _build_fastest_splits(df: pd.DataFrame) -> list:
    cells = []
    for col in SPLIT_COLS:
        valid = df[col].dropna()
        if valid.empty:
            continue
        row = df.loc[valid.idxmin()]
        cells.append(html.Div(className='split-card', children=[
            html.Div(col, className='split-label'),
            html.Div(_fmt_td(row[col]), className='split-time'),
            html.Div(row['Name'], className='split-name'),
        ]))
    return cells


def _build_median_splits(df: pd.DataFrame) -> list:
    """Card row showing median split time per discipline, grouped by class (no RELAY)."""
    filtered = df[df['Class'] != 'RELAY']
    cells = []
    for col in SPLIT_COLS:
        valid = filtered[col].dropna()
        if valid.empty:
            continue
        median_by_class = filtered.groupby('Class')[col].median().dropna()
        sub = [
            html.Div(f'{cls}: {_fmt_td(t)}', className='split-sub')
            for cls, t in median_by_class.items()
        ]
        cells.append(html.Div(className='split-card', children=[
            html.Div(col, className='split-label'),
            html.Div(_fmt_td(valid.median()), className='split-time'),
            *sub,
        ]))
    return cells


def make_layout(df: pd.DataFrame):
    return html.Div(className='page', children=[

        html.H1('Clonmel Triathlon Results', className='page-title'),

        # ── Race Summary ──────────────────────────────────────────────────────
        html.Section(className='section', children=[
            html.H2('Race Summary'),

            html.Div(className='kpi-row', children=_build_summary_stats(df)),

            html.Details(className='collapsible', children=[
                html.Summary('Fastest Splits'),
                html.Div(className='split-row', children=_build_fastest_splits(df)),
            ]),

            html.Details(className='collapsible', children=[
                html.Summary('Median Split Times'),
                html.Div(className='split-row', children=_build_median_splits(df)),
            ]),
        ]),

        html.Hr(),

        # ── Athlete Lookup ────────────────────────────────────────────────────
        html.Section(className='section', children=[
            html.H2('Athlete Lookup'),

            html.Div(className='controls-row', children=[
                html.Div(className='control-group control-group--wide', children=[
                    html.Label('Search athlete'),
                    dcc.Dropdown(
                        id='athlete-dropdown',
                        options=sorted(
                            [{'label': n, 'value': n} for n in df['Name'].dropna().unique()],
                            key=lambda o: o['label'],
                        ),
                        value=None,
                        placeholder='Type to search…',
                        searchable=True,
                        clearable=True,
                        className='athlete-dropdown',
                    ),
                ]),
                html.Div(className='control-group', children=[
                    html.Label('Grouping'),
                    dcc.Dropdown(
                        id='view-selector',
                        options=[
                            {'label': 'vs Class',      'value': 'class'},
                            {'label': 'vs Whole Race', 'value': 'overall'},
                            {'label': 'vs Age Group',  'value': 'ag'},
                            {'label': 'Normalised',    'value': 'norm'},
                            {'label': 'All (Extended)','value': 'extended'},
                        ],
                        value='class',
                        clearable=False,
                        className='view-dropdown',
                    ),
                ]),
            ]),

            html.Div(id='athlete-stats', className='athlete-stats'),

            dcc.Loading(
                id='chart-loading',
                type='circle',
                children=html.Img(id='athlete-chart', src='', className='athlete-chart'),
            ),
        ]),
    ])
