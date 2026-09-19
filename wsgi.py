"""WSGI entrypoint for production (gunicorn targets `wsgi:server`).

`python run.py` still works for local dev via Dash/Flask's own dev server;
this is what the Docker image uses instead, since that server explicitly
warns it isn't meant for production deployment.
"""
from sportsplits.app import create_app

server = create_app().server
