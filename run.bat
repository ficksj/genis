@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Сначала запусти setup.ps1
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "run.py"
