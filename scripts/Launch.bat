@echo off
REM PDF Text Recognizer Launch Script
REM Launches the standalone PDF text recognition application

cd /d "%~dp0"

echo.
echo =========================================================
echo   PDF Text Recognizer v1.0
echo =========================================================
echo.
echo Starting application...
echo.

REM Launch the GUI
python app\app_gui.py

REM Optionally open file explorer to show exe location
REM explorer.exe "%cd%\dist\"
