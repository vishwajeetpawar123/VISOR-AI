# Face Recognition Attendance System

## Project Overview
This is a lightweight Face Recognition Attendance System using Python, OpenCV, and Flask. It detects faces from the webcam, logs attendance, and serves a live dashboard accessible via web browser (desktop or mobile).

## How to Run (Three Ways)

### Option 1: The "Solid Program" (Executable)
I have compiled the program into a single file for you.
1. Go to the `dist` folder.
2. Run `AttendanceSystem.exe`.
   - *Note: This requires `faces` and `attendance_photos` folders to be in the same directory as the EXE.*
   - If you move the EXE, move those folders with it!

### Option 2: The "Scaled Down" Version (Source Code)
Use this for college submission. It is very small (< 10MB) without the environment.
1. **Delete** the `.venv` and `.venv_new` folders to save space (500MB -> 10MB).
2. **Delete** the `build` and `dist` folders if you don't need the EXE.
3. **Zip** the remaining files:
   - `final_attendance_app.py`
   - `requirements.txt`
   - `faces/`
   - `attendance_photos/`
   - `Run_Attendance.bat`
   - `README.md`

### Option 3: Developer Setup (on a new machine)
1. Install Python 3.9+.
2. Run the following commands:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   # If dlib fails, install the included wheel:
   pip install "dlib-19.22.99-cp39-cp39-win_amd64.whl"
   ```
3. Run `Run_Attendance.bat` or `python final_attendance_app.py`.

## Features
- **Face Detection**: Real-time using webcam.
- **Web Dashboard**: Open `http://localhost:5000` to see live logs.
- **Auto-Logging**: Records `lobby_log.csv`.
