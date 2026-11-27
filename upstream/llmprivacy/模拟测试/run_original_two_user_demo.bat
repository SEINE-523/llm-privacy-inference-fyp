@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
python -X utf8 run_original_two_user_demo.py
if errorlevel 1 (
  echo.
  echo The demo did not complete. Read the error above.
)
pause
