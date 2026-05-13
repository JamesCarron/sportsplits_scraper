import pandas as pd
from dash import Input, Output, html
from figure_utils import fig_to_base64, plot_single_panel, plot_comparison, _fmt_td
from visualise import plot_athlete_extended
from layout import _build_summary_stats, _build_fastest_splits, _build_median_splits


def _athlete_stat_spans(row) -> list:
    return [
        html.Span(f'Place: {int(row["Place"])}' if pd.notna(row["Place"]) else 'Place: —', className='stat'),
        html.Span(f'Class: {row["Class"]}',            className='stat'),
        html.Span(f'Age Group: {row["Age_Group"]}',    className='stat'),
        html.Span(f'Finish: {_fmt_td(row["Finish"])}', className='stat'),
        html.Span(f'Club: {row["Club"]}',              className='stat'),
    ]


def register_callbacks(app, race_dfs: dict):

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
