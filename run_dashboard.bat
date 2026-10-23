@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\streamlit.exe" (
    echo Streamlit is not installed. Run setup_and_run.bat first.
    pause
    exit /b 1
)
call ".venv\Scripts\activate.bat"
streamlit run app.py
