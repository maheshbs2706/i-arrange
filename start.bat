@echo off
rem Dev launcher: runs the app from source (no exe). Edit the code, run this again.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment, first run only...
    python -m venv .venv || goto :fail
    ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail
)

".venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo.
    echo The app exited with an error, see above.
    pause
)
exit /b

:fail
echo.
echo Setup failed. Check that Python 3.10 or newer is installed and on PATH.
pause
