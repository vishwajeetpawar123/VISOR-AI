@echo off
echo ===================================================
echo      VISOR AI - UPDATING FACE DATABASE
echo ===================================================
echo.
echo 1. Scanning "faces" folder...
echo 2. Generating high-precision SFace encodings...
echo.

set PYTHONIOENCODING=utf-8
.\.venv_new\Scripts\python.exe reencode_faces.py

echo.
echo ===================================================
echo                 DONE!
echo ===================================================
echo New faces have been added to the system.
echo You can now restart the attendance app.
echo.
pause
