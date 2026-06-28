import pandas as pd
from dash import dcc, html
from sportsplits.viz import fmt_td

SPLIT_COLS = ['Swim', 'T1', 'Bike', 'T2', 'Run', 'Finish']

# Classes that represent actual competitors (exclude DNS/DNF/DQ/NYS/RELAY)
_FINISH_CLASSES = {'Open', 'Female'}


def _kpi_card(label: str, value: str) -> html.Div:
    return html.Div(className='kpi-card', children=[
        html.Div(value, className='kpi-value'),
        html.Div(label, className='kpi-label'),
    ])


def _build_summary_stats(df: pd.DataFrame) -> list:
    finishers = df[df['Class'].isin(_FINISH_CLASSES)]
    class_counts = finishers['Class'].value_counts().to_dict()
    fastest_row = finishers.loc[finishers['Finish'].idxmin()]
    fastest_str = f'{fastest_row["Name"]} ({fmt_td(fastest_row["Finish"])})'
    return [
        _kpi_card('Total Finishers', str(len(finishers))),
        _kpi_card('Open', str(class_counts.get('Open', 0))),
        _kpi_card('Female', str(class_counts.get('Female', 0))),
        _kpi_card('Fastest Finisher', fastest_str),
    ]


def _build_fastest_splits(df: pd.DataFrame) -> list:
    finishers = df[df['Class'].isin(_FINISH_CLASSES)]
    cells = []
    for col in SPLIT_COLS:
        valid = finishers[col].dropna()
        if valid.empty:
            continue
        row = finishers.loc[valid.idxmin()]
        cells.append(html.Div(className='split-card', children=[
            html.Div(col, className='split-label'),
            html.Div(fmt_td(row[col]), className='split-time'),
            html.Div(row['Name'], className='split-name'),
        ]))
    return cells


def _build_median_splits(df: pd.DataFrame) -> list:
    finishers = df[df['Class'].isin(_FINISH_CLASSES)]
    cells = []
    for col in SPLIT_COLS:
        valid = finishers[col].dropna()
        if valid.empty:
            continue
        median_by_class = finishers.groupby('Class')[col].median().dropna()
        sub = [
            html.Div(f'{cls}: {fmt_td(t)}', className='split-sub')
            for cls, t in median_by_class.items()
        ]
        cells.append(html.Div(className='split-card', children=[
            html.Div(col, className='split-label'),
            html.Div(fmt_td(valid.median()), className='split-time'),
            *sub,
        ]))
    return cells


def make_layout(race_names: list):
    default_race = race_names[0]
    return html.Div(className='page', children=[

        html.H1('Triathlon Results Analyser', className='page-title'),

        # ── Race selector ─────────────────────────────────────────────────────
        html.Div(className='race-selector-row', children=[
            html.Label('Race', className='race-label'),
            dcc.Dropdown(
                id='race-selector',
                options=[{'label': n, 'value': n} for n in race_names],
                value=default_race,
                clearable=False,
                className='race-dropdown',
            ),
        ]),

        # ── Add a race from my.raceresult.com ─────────────────────────────────
        html.Details(className='add-race', children=[
            html.Summary('➕ Add a race from my.raceresult.com'),

            # Search the public event directory by name.
            html.Div(className='add-race-form', children=[
                dcc.Input(
                    id='search-input',
                    type='text',
                    placeholder='Search by event name (e.g. Jailbreak)…',
                    className='add-input add-input--url',
                    debounce=False,
                ),
                html.Button('Search', id='search-btn', n_clicks=0, className='add-btn'),
            ]),
            html.Div(id='search-status', className='add-race-status'),
            dcc.Loading(
                type='circle',
                children=dcc.RadioItems(
                    id='search-results',
                    options=[],
                    value=None,
                    className='search-results',
                    labelClassName='search-result',
                ),
            ),
            dcc.Loading(
                type='circle',
                children=html.Button(
                    'Add selected race', id='search-add-btn', n_clicks=0,
                    className='add-btn add-btn--wide',
                ),
            ),

            html.Hr(className='add-divider'),

            # Or paste a results URL / event id directly.
            html.Div('Or paste a results URL directly:', className='add-race-hint'),
            html.Div(className='add-race-form', children=[
                dcc.Input(
                    id='add-url',
                    type='text',
                    placeholder='https://my.raceresult.com/403737/',
                    className='add-input add-input--url',
                    debounce=True,
                ),
                dcc.Input(
                    id='add-name',
                    type='text',
                    placeholder='Display name (e.g. Jailbreak 2027)',
                    className='add-input add-input--name',
                    debounce=True,
                ),
                dcc.Loading(
                    type='circle',
                    children=html.Button('Add', id='add-race-btn', n_clicks=0, className='add-btn'),
                ),
            ]),
            html.Div(id='add-race-status', className='add-race-status'),
            html.Div(
                'Auto-detects the standard triathlon layout. The race is scraped, '
                'saved, and stays available after a restart.',
                className='add-race-hint',
            ),
        ]),

        # ── Race Summary ──────────────────────────────────────────────────────
        html.Section(className='section', children=[
            html.H2('Race Summary'),

            html.Div(id='summary-kpis', className='kpi-row'),

            html.Details(className='collapsible', children=[
                html.Summary('Fastest Splits'),
                html.Div(id='summary-fastest', className='split-row'),
            ]),

            html.Details(className='collapsible', children=[
                html.Summary('Median Split Times'),
                html.Div(id='summary-median', className='split-row'),
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
                        options=[],
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
                            {'label': 'vs Class',       'value': 'class'},
                            {'label': 'vs Whole Race',  'value': 'overall'},
                            {'label': 'vs Age Group',   'value': 'ag'},
                            {'label': 'Normalised',     'value': 'norm'},
                            {'label': 'All (Extended)', 'value': 'extended'},
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

        html.Hr(),

        # ── Athlete Comparison ────────────────────────────────────────────────
        html.Section(className='section', children=[
            html.H2('Athlete Comparison'),

            html.Div(className='controls-row', children=[
                html.Div(className='control-group control-group--wide', children=[
                    html.Label('Athlete A'),
                    dcc.Dropdown(
                        id='athlete-a-dropdown',
                        options=[],
                        value=None,
                        placeholder='Type to search…',
                        searchable=True,
                        clearable=True,
                    ),
                ]),
                html.Div(className='control-group control-group--wide', children=[
                    html.Label('Athlete B'),
                    dcc.Dropdown(
                        id='athlete-b-dropdown',
                        options=[],
                        value=None,
                        placeholder='Type to search…',
                        searchable=True,
                        clearable=True,
                    ),
                ]),
                html.Div(className='control-group', children=[
                    html.Label('View'),
                    dcc.Dropdown(
                        id='comparison-view-selector',
                        options=[
                            {'label': 'Split Times',    'value': 'times'},
                            {'label': 'vs Class',       'value': 'class'},
                            {'label': 'vs Whole Race',  'value': 'overall'},
                            {'label': 'vs Age Group',   'value': 'ag'},
                            {'label': 'Normalised',     'value': 'norm'},
                        ],
                        value='class',
                        clearable=False,
                    ),
                ]),
            ]),

            html.Div(id='comparison-stats', className='comparison-stats'),

            dcc.Loading(
                id='comparison-loading',
                type='circle',
                children=html.Img(id='comparison-chart', src='', className='athlete-chart'),
            ),
        ]),
    ])
