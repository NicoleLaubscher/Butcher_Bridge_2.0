@echo off
setlocal
if not exist .venv\Scripts\python.exe (
  echo The virtual environment is missing. Run setup_demo_windows.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
echo ButcherBridge will be available at http://127.0.0.1:5000
python run.py
pause

