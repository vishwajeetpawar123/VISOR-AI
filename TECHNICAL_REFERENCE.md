# Attendance System v2.5 - Technical Reference

**Purpose:** This document is an exhaustive reference manual for the Attendance System v2.5, designed for generating comprehensive mind maps and deep technical analysis. It covers every variable, logic gate, and architectural decision.

---

## 1. System Anatomy

### 1.1 File Structure

* **`final_attendance_app.py`**: The monolithic kernel. Contains:
  * *Configuration*: Paths, Thresholds (`EXIT_THRESHOLD=3.0`), and Modes.
  * *Web Server*: Flask application running in a **Daemon Thread**.
  * *Vision Loop*: Main infinite loop handling Camera, Detection, and Logic.
  * *Ollama Integration*: Chat interface with context-aware prompts.
* **`reencode_faces.py`**: The "Encoder" script.
  * *Role*: Off-line processing. Reads `faces/` directory, detects faces using **YuNet**, aligns them, and generates embeddings using **SFace**.
  * *Output*: Saves `face_encodings_sface.pkl`.
* **`face_encodings_sface.pkl`**: The "Knowledge Base".
  * *Format*: Python Pickle file.
  * *Content*: Dictionary `{'Name': numpy_array(128-d vector)}`.
* **`models/`**: The "Brain Stem".
  * `face_detection_yunet_2023mar.onnx`: YuNet Face Detector.
  * `face_recognition_sface_2021dec.onnx`: SFace Recognizer.
  * `haarcascade_eye_tree_eyeglasses.xml`: Start-of-the-art Eye Classifier for blink detection.
* **`attendance_photos/`**: The "Evidence Locker".
  * *Naming*: `Attendance_[SafeName]_[YYYYMMDD_HHMMSS].jpg`.
  * *Metadata*: Burned-in text overlay on the image itself.
* **`lobby_log.csv`**: The "Persistent Ledger".
  * *Schema*: `Timestamp, Event, Name, PhotoPath`.

### 1.2 Key Variables (The State)

* **`known_faces`** (Dict): Loaded from pickle. Maps Names to SFace Embeddings.
* **`present_people`** (Dict):
  * *Key*: Name (String).
  * *Value*: Last Seen Timestamp (Float, Unix Epic Time).
  * *Role*: Heartbeat mechanism to track presence in the "Lobby".
* **`frame_buffer`** (Global Variable):
  * *Role*: Shared memory buffer holding the current video frame.
  * *Access*: Written by Main Loop, Read by Flask Thread (for MJPEG stream).
* **`current_mode`** (String):
  * `SURVEILLANCE`: Passive, logging-only, night vision enabled.
  * `ATTENDANCE`: Interactive, requires Blink verification, Voice feedback.
* **`attn_state`** (State Machine):
  * Values: `SEARCHING`, `DETECTED`, `WAITING_BLINK`, `RECOGNIZING`, `COOLDOWN`.
  * *Role*: Controls the interactive flow in Attendance Mode.

---

## 2. The Computer Vision Pipeline (The "Brain")

This pipeline runs inside the `while True` loop of the main thread.

### Step 1: Acquisition & Enhancement

* **Source**: `cv2.VideoCapture(0)` @ 640x480.
* **Adaptive Night Vision**:
  * *Trigger*: Every 6th frame.
  * *Check*: Resize to 320x240 -> Calculate Mean Brightness.
  * *Action*: If brightness < 90, apply Gamma Correction (Gamma=1.7).
  * *Hysteresis*: Turns off only if brightness > 110.

### Step 2: Detection (YuNet)

* **Model**: YuNet (published in CVPR 2019).
* **Input**: Resized frame (320x240) for speed ("Ultra Lite").
* **Thresholds**: Confidence `0.6`, NMS `0.3`.
* **Output**: Bounding Box, Landmarks (Eyes, Nose, Mouth), Confidence.

### Step 3: Logic Branching (Modes)

#### Mode A: Surveillance (The "Ghost")

* **Frequency**: Every 6th frame.
* **Logic**:
    1. Detect Faces.
    2. **Recognition**: SFace Match (Cosine Distance).
    3. **Threshold**: `COSINE_THRESHOLD = 0.45`.
    4. **Action**: If Match Found, Log "ENTERED", update `present_people`.

#### Mode B: Attendance (The "Gatekeeper")

* **Frequency**: Every 3rd frame (Higher responsiveness).
* **State Machine**:
    1. **SEARCHING**: Scans for faces. Pick largest face.
    2. **DETECTED**: Voice prompt "Please blink".
    3. **WAITING_BLINK**:
        * Extract Eye ROI (Top 50% of face).
        * Run `haarcascade_eye_tree_eyeglasses.xml`.
        * Logic: If no eyes detected for >3 frames -> **BLINK CONFIRMED**.
    4. **RECOGNIZING**:
        * Run SFace Recognition.
        * If Match > 0.45 -> Voice "Attendance Registered".
        * Log Event.
    5. **COOLDOWN**: Prevents spamming.

### Step 4: Recognition (SFace)

* **Algorithm**: SphereFace (SFace) - Sigmoid-like loss function.
* **Input**: Aligned face crop (using 5 landmarks from YuNet).
* **Output**: 128-d Embedding.
* **Metric**: Cosine Similarity.

---

## 3. The Memory Architecture (RAM Strategy)

### 3.1 Threading Model (Single Process)

* **Main Thread**: Runs the Heavy Vision Loop (`cv2`, `numpy`, Neural Nets).
* **Daemon Thread**: Runs Flask (`app.run`).
* **IPC (Inter-Process Communication)**:
  * *Video*: Shared `frame_buffer` variable (Lock-less for speed, acceptable tearing risk).
  * *Control*: Global variables `current_mode`, `manual_recording_active`.
* **Memory Footprint**:
  * Reduced by ~40% compared to Multiprocessing.
  * Shared Address Space avoids pickling/serialization overhead.

### 3.2 Recording Strategy

* **Manual Trigger**: User presses REC button.
* **Format**: Tries `H.264` (avc1) first, falls back to `mp4v`, then `vp09`.
* **Chunking**: Automatically splits files every 10 minutes (`SEGMENT_DURATION = 600`) to prevent data loss.

---

## 4. The Web Interface (The "Frontend")

### 4.1 Backend (Flask)

* **API Design**: RESTful JSON endpoints.
* **Routes**:
  * `/api/chat`: **Ollama** Integration. Injects "Student Notes" + "Lobby Logs" into System Prompt.
  * `/api/logs`: Returns last 500 CSV entries (Reversed).
  * `/api/notes`: Read/Write `student_notes.md`.
  * `/video_feed`: MJPEG Stream Generator.

### 4.2 Frontend (Stripe-Inspired Glassmorphism)

* **Tech**: Vanilla HTML/CSS/JS (Single File).
* **Visuals**:
  * Mesh Gradient Background.
  * Glassy Cards (`backdrop-filter: blur(20px)`).
  * Responsive Grid Layout.
* **Tabs**: Live Feed, Logs, Photos, Recordings, Notes.
* **Real-time Interaction**:
  * Settings Sidebar (Mode Switch, Threshold).
  * Live Chat with AI (Typing indicators, Auto-scroll).

---

## 5. Logic Trace: The "Entry" Event

What happens when "User X" walks in?

1. **Detection**: YuNet finds face at (x,y).
2. **Mode Check**:
    * *Surveillance*: Immediate Recognition.
    * *Attendance*: Wait for Blink -> Trigger Recognition.
3. **Matching**: Embedding `v1` vs Known `v2`. Score `0.72` (> 0.45).
4. **Lobby Check**: `if "User X" not in present_people`.
5. **Action Trigger**:
    * **Log**: CSV Append `Timestamp, ENTERED, User X, PhotoPath`.
    * **Evidence**: Frame copied -> Timestamp burned -> Saved to JPG.
6. **Heartbeat**: `present_people["User X"] = Now()`.

---

## 6. Logic Trace: The "Exit" Event (The 3-Second Rule)

1. **Loop**: Every frame, iterate `present_people`.
2. **Check**: `Now() - last_seen_timestamp`.
3. **Threshold**: If `Diff > 3.0` Seconds.
4. **Action**:
    * **Log**: CSV Append `Timestamp, EXITED, User X`.
    * **Cleanup**: Remove "User X" from `present_people` dict.

---

## 7. AI Assistant Integration (Ollama)

* **Model**: `qwen2.5:7b` (Configurable).
* **Context Window**:
  * **System Prompt**: "You are Visor..."
  * **Dynamic Data**: Injects content of `student_notes.md` + Last 500 Logs.
* **Capabilities**:
  * "Who is here right now?" (Parses Logs).
  * "Is John in trouble?" (Reads Notes).
