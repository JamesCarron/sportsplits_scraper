import matplotlib
matplotlib.use('Agg')  # must be before any other matplotlib import

import dash
from races import load_all
from layout import make_layout
from callbacks import register_callbacks

RACE_DFS = load_all()

app = dash.Dash(__name__, title='Triathlon Results Analyser')
app.layout = make_layout(list(RACE_DFS.keys()))
register_callbacks(app, RACE_DFS)

if __name__ == '__main__':
    app.run(debug=False, port=8050)
