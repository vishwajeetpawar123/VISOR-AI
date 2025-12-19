@echo off
echo Building Attendance System Executable...
echo This may take a few minutes.

:: Clean previous builds
if exist build rd /s /q build
if exist dist rd /s /q dist

:: Run PyInstaller using .venv_new or .venv
if exist .venv_new\Scripts\pyinstaller.exe (
    set PYINSTALLER=.venv_new\Scripts\pyinstaller.exe
) else (
    set PYINSTALLER=.venv\Scripts\pyinstaller.exe
)

echo Using: %PYINSTALLER%

%PYINSTALLER% --onefile --name "AttendanceSystem" --clean final_attendance_app.py --hidden-import=face_recognition_models --collect-all face_recognition_models --collect-all cv2

echo.
echo Build Complete!
echo You can find your new "solid program" in the 'dist' folder.
pause
