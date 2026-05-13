import matplotlib
matplotlib.use('Agg')  # must be before any other matplotlib import

import dash
from metrics import build_metrics
from layout import make_layout
from callbacks import register_callbacks

DF = build_metrics('Clonmel.txt')

app = dash.Dash(__name__, title='Triathlon Results Analyser')
app.layout = make_layout(DF)
register_callbacks(app, DF)

if __name__ == '__main__':
    app.run(debug=False, port=8050)
