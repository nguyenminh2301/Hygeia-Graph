@echo off
REM Hygeia-Graph Local Runner
REM Uses local python environment. Make sure python and streamlit are in PATH.

echo ========================================
echo Hygeia-Graph Environment Launcher
echo ========================================

REM Add src to PYTHONPATH so imports work
set PYTHONPATH=%PYTHONPATH%;%~dp0src

REM Check if streamlit is installed
python -c "import streamlit" 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Streamlit not found in current python environment.
    echo Please ensure you have installed requirements: pip install -r requirements.txt
    pause
    exit /b 1
)

echo Starting Streamlit App...
streamlit run app.py

pause
