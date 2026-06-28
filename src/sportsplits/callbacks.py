import json

import pandas as pd
from dash import Input, Output, State, ctx, html, no_update
from sportsplits.viz import fmt_td
from sportsplits.viz.web import fig_to_base64, plot_single_panel, plot_comparison
from sportsplits.viz.notebook import plot_athlete_extended
from sportsplits.layout import _build_summary_stats, _build_fastest_splits, _build_median_splits
from sportsplits.races import add_race_from_url
from sportsplits.parsers.raceresult.common import search_events


def _athlete_stat_spans(row) -> list:
    return [
        html.Span(f'Place: {int(row["Place"])}' if pd.notna(row["Place"]) else 'Place: —', className='stat'),
        html.Span(f'Class: {row["Class"]}',            className='stat'),
        html.Span(f'Age Group: {row["Age_Group"]}',    className='stat'),
        html.Span(f'Finish: {fmt_td(row["Finish"])}', className='stat'),
        html.Span(f'Club: {row["Club"]}',              className='stat'),
    ]


def register_callbacks(app, race_dfs: dict):

    @app.callback(
        Output('search-results', 'options'),
        Output('search-results', 'value'),
        Output('search-status', 'children'),
        Input('search-btn', 'n_clicks'),
        Input('search-input', 'n_submit'),
        State('search-input', 'value'),
        prevent_initial_call=True,
    )
    def search_races(n_clicks, n_submit, query):
        query = (query or '').strip()
        if not query:
            return [], None, html.Span('Type an event name to search.', className='add-error')
        try:
            events = search_events(query)
        except Exception as exc:
            return [], None, html.Span(f'Search failed: {exc}', className='add-error')
        if not events:
            return [], None, html.Span(f'No events found for "{query}".', className='add-race-hint')

        options = []
        for e in events:
            where = ', '.join(x for x in (e['location'], e['country']) if x)
            label = f"{e['name']}  —  {e['date']}  ·  {e['type']}"
            if where:
                label += f"  ·  {where}"
            options.append({'label': label, 'value': json.dumps({'id': e['id'], 'name': e['name']})})
        return options, None, html.Span(f'{len(events)} event(s) found.', className='add-race-hint')

    @app.callback(
        Output('race-selector', 'options'),
        Output('race-selector', 'value'),
        Output('add-race-status', 'children'),
        Input('add-race-btn', 'n_clicks'),
        Input('search-add-btn', 'n_clicks'),
        State('add-url', 'value'),
        State('add-name', 'value'),
        State('search-results', 'value'),
        prevent_initial_call=True,
    )
    def add_race(manual_clicks, search_clicks, url, name, selected):
        if ctx.triggered_id == 'search-add-btn':
            if not selected:
                return no_update, no_update, html.Span(
                    'Pick an event from the search results first.', className='add-error')
            chosen = json.loads(selected)
            url, name = str(chosen['id']), chosen['name']
        else:
            url = (url or '').strip()
            name = (name or '').strip()
            if not url or not name:
                return no_update, no_update, html.Span(
                    'Enter both a results URL and a display name.', className='add-error')

        try:
            df = add_race_from_url(url, name, race_dfs)
        except Exception as exc:
            return no_update, no_update, html.Span(f'Could not add race: {exc}', className='add-error')

        options = [{'label': n, 'value': n} for n in race_dfs]
        return options, name, html.Span(
            f'Added "{name}" — {len(df)} athletes loaded.', className='add-ok')

    @app.callback(
        Output('summary-kpis', 'children'),
        Output('summary-fastest', 'children'),
        Output('summary-median', 'children'),
        Output('athlete-dropdown', 'options'),
        Output('athlete-dropdown', 'value'),
        Output('athlete-a-dropdown', 'options'),
        Output('athlete-a-dropdown', 'value'),
        Output('athlete-b-dropdown', 'options'),
        Output('athlete-b-dropdown', 'value'),
        Input('race-selector', 'value'),
    )
    def update_race(race_name):
        df = race_dfs[race_name]
        athlete_options = sorted(
            [{'label': n, 'value': n} for n in df['Name'].dropna().unique()],
            key=lambda o: o['label'],
        )
        return (
            _build_summary_stats(df),
            _build_fastest_splits(df),
            _build_median_splits(df),
            athlete_options, None,
            athlete_options, None,
            athlete_options, None,
        )

    @app.callback(
        Output('athlete-chart', 'src'),
        Output('athlete-stats', 'children'),
        Input('athlete-dropdown', 'value'),
        Input('view-selector', 'value'),
        Input('race-selector', 'value'),
    )
    def render_chart(athlete_name, view, race_name):
        if not athlete_name:
            return '', ''

        df = race_dfs[race_name]

        if view == 'extended':
            fig = plot_athlete_extended(athlete_name, df)
        else:
            fig = plot_single_panel(athlete_name, view, df)

        if fig is None:
            return '', html.P(f'Could not render chart for "{athlete_name}".')

        row = df[df['Name'] == athlete_name].iloc[0]
        stats = html.Div(className='stats-bar', children=_athlete_stat_spans(row))
        return fig_to_base64(fig), stats

    @app.callback(
        Output('comparison-chart', 'src'),
        Output('comparison-stats', 'children'),
        Input('athlete-a-dropdown', 'value'),
        Input('athlete-b-dropdown', 'value'),
        Input('comparison-view-selector', 'value'),
        Input('race-selector', 'value'),
    )
    def render_comparison(name_a, name_b, view, race_name):
        if not name_a or not name_b:
            return '', ''

        df = race_dfs[race_name]
        fig = plot_comparison(name_a, name_b, view, df)

        if fig is None:
            return '', html.P('Could not render comparison — check athlete names.')

        row_a = df[df['Name'] == name_a].iloc[0]
        row_b = df[df['Name'] == name_b].iloc[0]

        stats = html.Div(className='comparison-stats', children=[
            html.Div(className='athlete-col athlete-col--a', children=[
                html.Div(name_a, className='athlete-col-name'),
                *_athlete_stat_spans(row_a),
            ]),
            html.Div(className='athlete-col athlete-col--b', children=[
                html.Div(name_b, className='athlete-col-name'),
                *_athlete_stat_spans(row_b),
            ]),
        ])

        return fig_to_base64(fig), stats
