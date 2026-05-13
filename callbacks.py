import pandas as pd
from dash import Input, Output, html
from figure_utils import fig_to_base64, plot_single_panel, _fmt_td
from visualise import plot_athlete_extended


def register_callbacks(app, df: pd.DataFrame):

    @app.callback(
        Output('athlete-chart', 'src'),
        Output('athlete-stats', 'children'),
        Input('athlete-dropdown', 'value'),
        Input('view-selector', 'value'),
    )
    def render_chart(athlete_name, view):
        if not athlete_name:
            return '', ''

        if view == 'extended':
            fig = plot_athlete_extended(athlete_name, df)
        else:
            fig = plot_single_panel(athlete_name, view, df)

        if fig is None:
            return '', html.P(f'Could not render chart for "{athlete_name}".')

        src = fig_to_base64(fig)

        row = df[df['Name'] == athlete_name].iloc[0]
        stats = html.Div(className='stats-bar', children=[
            html.Span(f'Place: {int(row["Place"])}',        className='stat'),
            html.Span(f'Class: {row["Class"]}',             className='stat'),
            html.Span(f'Age Group: {row["Age_Group"]}',     className='stat'),
            html.Span(f'Finish: {_fmt_td(row["Finish"])}',  className='stat'),
            html.Span(f'Club: {row["Club"]}',               className='stat'),
        ])

        return src, stats
