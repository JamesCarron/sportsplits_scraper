# Triathlon Results Analyser — Dash app.
#
# All the race data the app reads at startup (data/processed/*.csv,
# data/raw/sportsplits/*.json, a few small data/raw/ root files) is baked
# into the image rather than fetched live -- this is a static analysis
# tool over a fixed, already-scraped dataset, not a live-scraping service.
# See .dockerignore for what's deliberately left out (~190MB of raw
# scrape/process-time-only input under data/raw/).
FROM python:3.11-slim

WORKDIR /app

# Installed from pyproject.toml first (separate layer) so an app code
# change doesn't force a dependency reinstall.
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

COPY data/ ./data/
COPY wsgi.py ./

EXPOSE 8050

# --workers 1: the app precomputes every chart/table once at startup and
# serves from memory (see age_group_page.py's own docstring) -- a second
# worker would redo that ~60-90s startup cost and double the memory for no
# benefit. --threads for modest concurrency without a second process.
# --timeout well above gunicorn's 30s default: that startup precompute
# runs during the worker's boot, before it can send gunicorn a heartbeat,
# and gunicorn kills workers that go quiet longer than --timeout.
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--workers", "1", "--threads", "4", \
     "--timeout", "300", "wsgi:server"]
