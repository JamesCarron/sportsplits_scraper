"""WSGI entrypoint for production (gunicorn targets `wsgi:server`).

`python run.py` still works for local dev via Dash/Flask's own dev server;
this is what the Docker image uses instead, since that server explicitly
warns it isn't meant for production deployment.

Same sys.path trick as run.py, and for the same reason: config.py's
PROJECT_ROOT is computed relative to its own file location, assuming a
`<this file's dir>/src/sportsplits/...` layout. `pip install .` flattens
src/ away when it installs into site-packages, which silently breaks that
assumption -- every data path resolves under the Python install directory
instead of the app's own data/. Importing sportsplits from ./src directly
(checked before site-packages, since it's inserted at position 0) keeps
the layout config.py expects, regardless of whether the package also got
pip-installed (harmless if so -- it's just unused).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from sportsplits.app import create_app

server = create_app().server
