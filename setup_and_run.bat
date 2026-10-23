@echo off
setlocal
cd /d "%~dp0"
title PulseIQ Analytics - Setup and Run

echo ==========================================
echo         PulseIQ Analytics Setup
echo ==========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Creating Python 3.10 virtual environment...
    py -3.10 -m venv .venv
    if errorlevel 1 goto :failed
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :failed

echo Installing project dependencies...
python -m pip install --upgrade pip
if errorlevel 1 goto :failed
python -m pip install -r requirements.txt
if errorlevel 1 goto :failed

if not exist ".env" copy ".env.example" ".env" >nul

echo.
echo Running ETL, warehouse, contracts, metrics and quality checks...
python run_pipeline.py
if errorlevel 1 goto :failed

echo.
echo Running automated tests...
python -m pytest -q
if errorlevel 1 goto :failed

echo.
echo Pipeline and test steps finished. Review the reports folder.
echo Start the dashboard later with: run_dashboard.bat
pause
exit /b 0

:failed
echo.
echo A setup, pipeline, or test step failed. Read the error above.
echo If you need help, copy the complete error message.
pause
exit /b 1
