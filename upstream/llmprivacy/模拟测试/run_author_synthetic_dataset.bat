@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
python -X utf8 run_author_synthetic_dataset.py %*
if errorlevel 1 (
  echo.
  echo The author dataset run did not complete. Read the error above.
)
pause