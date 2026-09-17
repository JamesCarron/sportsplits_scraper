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

echo Starting the app... your browser will open automatically once it's ready.

REM Poll the port in the background and open the browser as soon as the app
REM responds (startup can take a while - it loads/precomputes every race).
start "" powershell -NoProfile -WindowStyle Hidden -Command "while (-not (Test-NetConnection -ComputerName localhost -Port 8050 -InformationLevel Quiet -WarningAction SilentlyContinue)) { Start-Sleep -Seconds 1 }; Start-Process 'http://localhost:8050'"

"%PY%" run.py

REM Keep the window open if the server exits or errors.
echo.
echo The app has stopped.
pause
