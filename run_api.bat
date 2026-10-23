@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\uvicorn.exe" (
    echo API dependencies are not installed. Run setup_and_run.bat first.
    pause
    exit /b 1
)
call ".venv\Scripts\activate.bat"
uvicorn api:app --reload
