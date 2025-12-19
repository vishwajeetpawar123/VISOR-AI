# Attendance System v2.5 - "Teeth to Bone" Technical Reference

**Purpose:** This document is an exhaustive reference manual for the Attendance System v2.5, designed for generating comprehensive mind maps and deep technical analysis. It covers every variable, logic gate, and architectural decision.

---

[VISUAL UNDERSTANGING](Digital_Sentry_Architectural_Tour.pdf)

## 1. System Anatomy

### 1.1 File Structure
*   **`final_attendance_app.py`**: The simplified monolithic kernel. Contains:
    *   *Configuration Constants*: Settings for paths and timeouts.
    *   *Web Server Class*: Flask application definitions.
    *   *Vision Logic*: OpenCV and Face Recognition loops.
    *   *Process Management*: Multiprocessing entry point.
*   **`faces/`**: The "Knowledge Base".
    *   *Input*: `.jpg` or `.png` images of known individuals.
    *   *Processing*: Read at startup to generate 128-dimensional vector embeddings.
*   **`attendance_photos/`**: The "Evidence Locker".
    *   *Output*: Time-stamped images of people recognized by the system.
    *   *Naming Convention*: `Attendance_[Name]_[YYYYMMDD_HHMMSS].jpg`.
*   **`lobby_log.csv`**: The "Persistent Ledger".
    *   *Schema*: `Timestamp, Event, Name, PhotoPath`
    *   *Events*: "ENTERED", "EXITED".

### 1.2 Key Variables (The State)
*   **`known_face_encodings`** (List of Lists): The mathematical representation of every face in `faces/`. Each item is an array of 128 floating-point numbers.
*   **`known_face_names`** (List of Strings): Parallel list to `encodings`. Index `i` in `names` corresponds to Index `i` in `encodings`.
*   **`present_people`** (Dictionary):
    *   *Key*: Name (String, e.g., "Vishwash").
    *   *Value*: Last Seen Timestamp (Float, Unix Epic Time).
    *   *Role*: Tracks who is currently standing in front of the camera to prevent duplicate logs and detect when they leave.
*   **`process_this_frame`** (Integer): A counter used for modulo arithmetic to trigger the heavy face recognition logic only on specific frames.
*   **`server_process`** (multiprocessing.Process): A handle to the child process running the Flask web server. Is `None` when server is OFF.

---

## 2. The Computer Vision Pipeline (The "Brain")

This pipeline runs inside the `while True` loop of the main process.

### Step 1: Acquisition
*   **Source**: `cv2.VideoCapture(0)` (Default Webcam).
*   **Raw Data**: A numpy array of shape `(480, 640, 3)` (Height, Width, BGR Channels).

### Step 2: Pre-processing (The CPU Optimization)
*   **Resizing**: `cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)`
    *   *Input*: 307,200 pixels.
    *   *Output*: 19,200 pixels (160x120).
    *   *Why*: Reduces dimensionality for the O(N^2) or O(N log N) complexity of detection algorithms.
*   **Color Conversion**:
    *   *Haar needs*: Grayscale (`cv2.cvtColor(..., cv2.COLOR_BGR2GRAY)`).
    *   *dlib needs*: RGB (`cv2.cvtColor(..., cv2.COLOR_BGR2RGB)`).

### Step 3: Detection (Haar Cascade)
*   **Algorithm**: Viola-Jones Object Detection Framework.
*   **Mechanism**: Slides a window over the grayscale image seeking Haar-like features (e.g., bridge of nose is lighter than eyes).
*   **Settings**: `scaleFactor=1.1`, `minNeighbors=5`.
*   **Output**: List of Rectangles `[(x, y, w, h)]`. Represents *where* a face is, not *who* it is.

### Step 4: Recognition (dlib ResNet)
*   **Gate**: Only runs if `process_this_frame % 5 == 0`.
*   **Encoding**:
    *   The 160x120 RGB image + The Rectangle locations are passed to `face_recognition.face_encodings`.
    *   dlib aligns the face landmarks (eyes, nose, chin).
    *   It passes the aligned face through a Deep ResNet Model.
    *   **Output**: A 128-d vector (embedding).
*   **Matching**:
    *   **Euclidean Distance**: Calculates the geometric distance between the live vector and all `known_face_encodings`.
    *   **Threshold**: Default tolerance is 0.6.
    *   **Verdict**: The name with the smallest distance (if < 0.6) is the match.

---

## 3. The Memory Architecture (RAM Strategy)

### 3.1 The "Heavy" Process (Main)
*   **Loads**: `cv2` (OpenCV), `numpy`, `face_recognition` (wrapper), `dlib` (C++ Engine).
*   **Memory Footprint**:
    *   Python Interpreter: ~20MB
    *   dlib Models (`shape_predictor_68_face_landmarks.dat` + `resnet_model_v1.dat`): ~500MB
    *   Video Buffers: ~50MB
    *   **Total**: ~600MB.

### 3.2 The "Light" Process (Web Server)
*   **Trigger**: Spawns only when user presses 's'.
*   **Loads**: `flask`, `socket`, `threading`.
*   **Crucial Optimization**: The `import face_recognition` statement is *hidden* inside the Main Loop function scope. Therefore, this process *never* imports dlib.
*   **Memory Footprint**: ~30MB.
*   **Lifecycle**:
    *   *Start*: `multiprocessing.Process(target=run_flask_app).start()` -> Clones interpreter -> Imports Flask -> Listens on Port 5000.
    *   *Stop*: `process.terminate()` -> SIGTERM signal -> Memory instantly released to OS.

---

## 4. The Web Interface (The "Frontend")

### 4.1 Backend (Flask)
*   **Route `/`**: Serves `HTML_TEMPLATE`.
*   **Route `/api/photos`**:
    *   Scans `attendance_photos/`.
    *   Sorts by `os.path.getmtime` (Reverse).
    *   Parses filenames to human-readable names.
    *   Returns JSON: `[{"url": "/photos/...", "name": "...", "timestamp": "..."}]`
*   **Route `/photos/<filename>`**: Static file server for the images.

### 4.2 Frontend (HTML/JS)
*   **Styling**: Dark Mode CSS Variables (`--bg-color: #0d1117`).
*   **Logic**:
    *   `fetchPhotos()`: Async Await function.
    *   **Data Binding**: Compares `grid.dataset.key` (a hash of current filenames) vs new filenames. Only updates DOM if changed (Virtual DOM concept).
    *   **Injection**: Appends HTML Strings to the Grid Container.

---

## 5. Logic Trace: The "Entry" Event

What happens when "User X" walks in?

1.  **Frame N**: Camera captures User X.
2.  **Detection**: Haar Cascade finds a face rectangle.
3.  **Recognition**: dlib computes vector, matches to "User X".
4.  **State Check**: Code checks `if "User X" in present_people`.
    *   *Result*: False.
5.  **Action Trigger**:
    *   **Log**: Appends line to csv: `2023-10-27 10:00:00,ENTERED,User X,...`
    *   **Evidence**:
        *   Copies current frame.
        *   `cv2.putText`: Burns "10:00:00 - User X" in red text onto the pixels.
        *   `cv2.imwrite`: Saves JPG to disk.
6.  **State Update**: `present_people["User X"] = <Current Time>`.

---

## 6. Logic Trace: The "Exit" Event

1.  **Frame N+100**: User X walks away.
2.  **Detection**: No faces found.
3.  **Loop**: Code iterates through keys in `present_people`.
4.  **Timestamp Check**: `Current Time - present_people["User X"]`.
    *   *Value*: 3.1 seconds.
    *   *Threshold*: 3.0 seconds.
5.  **Action Trigger**:
    *   **Log**: Appends line to csv: `...,EXITED,User X`
    *   **State Update**: `del present_people["User X"]`.
