@echo off
TITLE Face Recognition Attendance System
echo Starting Camera...
echo Press 'q' in the camera window to close detection.

:: Change directory to the folder where this file is located
cd /d "%~dp0"

:: Check which venv exists
if exist .venv_new\Scripts\python.exe (
    set PYTHON_EXE=.venv_new\Scripts\python.exe
) else (
    set PYTHON_EXE=.venv\Scripts\python.exe
)

echo Using Python: %PYTHON_EXE%

:: Run the script
"%PYTHON_EXE%" final_attendance_app.py

:: Pause so the user can see errors if it crashes
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo The application crashed or closed with an error.
    pause
)
