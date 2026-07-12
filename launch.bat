@echo off
REM Launch the Triathlon Results Analyser (Dash app).
REM Uses the project's virtualenv Python if present, otherwise the system Python.
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

echo Starting the app... open http://localhost:8050 in your browser.
"%PY%" run.py

REM Keep the window open if the server exits or errors.
echo.
echo The app has stopped.
pause
