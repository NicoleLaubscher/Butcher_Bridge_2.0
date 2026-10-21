@echo off
setlocal
echo Setting up ButcherBridge with the offline SQLite demonstration database...
py -3 -m venv .venv
if errorlevel 1 goto :error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist .env copy .env.demo.example .env
python seed.py --reset
if errorlevel 1 goto :error
echo.
echo Setup complete. Double-click run_windows.bat to open the server.
pause
exit /b 0
:error
echo.
echo Setup failed. Confirm that Python 3 is installed and available as "py".
pause
exit /b 1

