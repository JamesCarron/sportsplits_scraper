import matplotlib
matplotlib.use('Agg')  # must be before any other matplotlib import

import dash

from sportsplits.races import REGISTRY, load_all
from sportsplits.layout import make_layout
from sportsplits.callbacks import register_callbacks
from sportsplits import age_group_page


def create_app() -> dash.Dash:
    """Build the Dash app: load every race, wire up the layout and callbacks.

    Dash(__name__) resolves the assets/ folder next to this module
    (src/sportsplits/assets/), so the stylesheet is served automatically.
    """
    race_dfs = load_all()
    age_group_pro_content, age_group_regular_content, age_group_ireland_content = age_group_page.build_all_content()
    app = dash.Dash(__name__, title='Triathlon Results Analyser')
    # REGISTRY, not race_dfs: the dropdown must list every selectable race,
    # including the lazy-loaded regular Ironman races load_all() deliberately
    # skipped (races.py's _LAZY_LOAD_NAMES) -- race_dfs only holds what's
    # been loaded so far.
    app.layout = make_layout(list(REGISTRY.keys()), age_group_pro_content, age_group_regular_content, age_group_ireland_content)
    register_callbacks(app, race_dfs)
    return app


def main() -> None:
    create_app().run(debug=False, port=8050)


if __name__ == '__main__':
    main()
