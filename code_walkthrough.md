# Comprehensive Code Walkthrough: Visor AI Attendance System v2.5

This document dissects `final_attendance_app.py` line-by-line, explaining the *why* and *how* behind every decision. It is designed to be uploaded to NotebookLM for deep learning and mind-mapping.

---

## **Part 1: The Foundation (Imports & Config)**

These lines set up the environment and import necessary tools.

### **Lines 1-9: Essential Libraries**

```python
1: import os
2: import cv2
3: import numpy as np
4: import time
5: import socket 
6: from datetime import datetime
7: import threading
8: import logging
9: from flask import Flask, render_template_string, jsonify, send_from_directory, request, Response
```

* **`import os`**: Used for interacting with the operating system (creating folders, finding file paths).
* **`import cv2` (OpenCV)**: The core computer vision library. We use this to read the camera, process images (resize, grayscale), and draw boxes on the screen.
* **`import numpy as np`**: Short for "Numerical Python". Images in OpenCV are just giant grids of numbers (matrices). NumPy lets us do math on these grids efficiently.
* **`import time`**: Used for measuring delays (e.g., waiting 3 seconds before marking someone as "Exited") and controlling frame rate.
* **`import socket`**: Used to find your computer's local IP address (e.g., `192.168.1.5`) so you can access the app from your phone.
* **`from datetime import datetime`**: Used to generate timestamps like "2023-10-27 10:30:00 AM" for logs.
* **`import threading`**: **CRITICAL**. This allows us to run the Flask Web Server and the Camera Loop at the same time. Without this, the camera would freeze while the website loads, or vice versa.
* **`import logging`**: Used to silence Flask's noisy output in the console so we can see our own print statements clearly.
* **`from flask import ...`**: Flask is the micro-web framework. It lets us turn Python functions into web pages.

### **Lines 14-29: Configuration Constants**

```python
17: BASE_DIR = os.getcwd()
18: manual_recording_active = False 
19: frame_buffer = None 
20: show_local_preview = True 
...
26: OLLAMA_URL = "http://localhost:11434/api/generate"
27: OLLAMA_MODEL = "qwen2.5:7b"
28: current_mode = "SURVEILLANCE" 
```

* **`BASE_DIR`**: Ensures we know exactly where we are running from.
* **`frame_buffer`**: A global variable that holds the *latest* camera frame. The camera thread writes to it, and the web server thread reads from it. This is how the live stream works.
* **`show_local_preview`**: A toggle. If `True`, a window pops up on the PC. If `False`, it runs silently (headless).
* **`current_mode`**: The system has two brains: "SURVEILLANCE" (passive logging) and "ATTENDANCE" (active interaction). This variable switches between them.

---

## **Part 2: The User Interface (HTML/CSS)**

Lines 33-614 contain a giant string `HTML_TEMPLATE`. This is the entire website frontend embedded directly into the Python file.

### **Why embed it?**

To make the application "Single File Portable". You don't need a separate `templates` folder; everything is in `final_attendance_app.py`.

### **Key Sections of the UI:**

* **CSS Grid Layout (`.main-layout`)**: Splits the screen into three columns: Settings (Left), Main Content (Center), Chat (Right).
* **Glassmorphism (`backdrop-filter: blur(20px)`)**: Creates that modern, frosted-glass effect you see on the cards.
* **JavaScript Logic (`<script>`)**:
  * **`render()`**: The main function that decides what to show (Live Feed, Logs, or Photos).
  * **`fetch('/api/...')`**: This is how the website asks Python for data without reloading the page (AJAX).

---

## **Part 3: The Web Server (Flask Routes)**

This section handles requests from the browser.

### **The "API" (Application Programming Interface)**

```python
624: @app.route('/api/record', methods=['POST'])
625: def toggle_record():
626:     global manual_recording_active
627:     manual_recording_active = not manual_recording_active
628:     return jsonify({'status': manual_recording_active})
```

* **`@app.route`**: A "Decorator". It tells Flask: "When someone visits `/api/record`, run this function."
* **`global manual_recording_active`**: We need to modify the global variable so the camera loop knows to start/stop recording.

### **The Video Stream Generator (Lines 730-756)**

```python
730: def generate_frames():
...
749:             ret, buffer = cv2.imencode('.jpg', frame_buffer)
751:             yield (b'--frame\r\n' ... )
```

* **`cv2.imencode('.jpg', frame_buffer)`**: Compresses the raw image into a JPEG (much smaller size for sending over network).
* **`yield`**: This is a "Generator". Instead of returning one value, it pumps out a continuous stream of data. This creates the "Motion JPEG" (MJPEG) stream that browsers treat as a video.

### **The Chatbot Logic (Lines 809-865)**

```python
821:     system_prompt = (
822:         f"Current System Time: {current_time_str}\\n"
823:         "You are 'Visor'... Use 'Student Notes'..."
...
855:         response = requests.post(OLLAMA_URL, json=payload...)
```

* **RAG (Retrieval-Augmented Generation)**: We inject "Context" (Logs + Notes) into the prompt *before* sending it to the AI.
* **`requests.post(OLLAMA_URL...)`**: This sends the text to your local AI (AirLLM/Ollama) and waits for a reply.

---

## **Part 4: The Core Logic (Computer Vision)**

This is where the magic happens.

### **Logging Events (Lines 890-920)**

```python
890: def log_event(event, name, frame=None):
...
906:         cv2.putText(evidence_frame, f"{now_str} - {name}"...)
909:         cv2.imwrite(photo_filename, evidence_frame)
```

* **Evidence Creation**: We don't just save the image; we "burn" the timestamp into the pixels using `cv2.putText`. This prevents tampering (you can't just change the file metadata).

### **Initialization (Lines 921-1065)**

```python
1003:     detector = cv2.FaceDetectorYN.create(...)
1008:     recognizer = cv2.FaceRecognizerSF.create(...)
```

* **YuNet (`FaceDetectorYN`)**: A lightweight model that finds *where* faces are (bounding box).
* **SFace (`FaceRecognizerSF`)**: A model that turns a face into a "vector" (a list of numbers). If two vectors are close (Cosine Similarity), it's the same person.

### **Adaptive Night Vision (Lines 1094-1107)**

```python
1097:             small_check = cv2.resize(frame, (320, 240))
1098:             avg_brightness = np.mean(small_check)
1099:             if avg_brightness < 90:
1100:                 night_vision_active = True
1106:             frame = adjust_gamma(frame, 1.7)
```

* **Why resize?** Checking brightness on a 4K image is slow. Resizing to 320x240 makes it lightning fast.
* **`np.mean`**: Calculates the average pixel intensity (0=Black, 255=White).
* **Gamma Correction**: A mathematical trick to brighten dark areas without washing out bright areas.

---

## **Part 5: The Infinite Loop (Main Logic)**

### **The Mode Switcher**

The code splits into two main blocks inside the loop:

#### **Mode 1: Surveillance (Lines 1164-1206)**

* **Optimization**: Runs detection only every **6th frame**. Why? Because surveillance doesn't need to be instant. This saves huge amounts of CPU.
* **Passive**: It just logs "ENTERED" and updates the `present_people` list. It does NOT speak or ask for blinks.

#### **Mode 2: Attendance (Lines 1210-1350)**

* **State Machine**:
    1. **SEARCHING**: Looking for a face.
    2. **DETECTED**: Found a face, checks if it's stable for 1 second.
    3. **WAITING_BLINK**:
        * Extracts the "Eye ROI" (Region of Interest).
        * Uses `haarcascade_eye` to see if eyes are open.
        * Logic: If eyes were open, then closed, then open -> **BLINK!**
    4. **RECOGNIZING**: Only runs the heavy SFace model *after* the blink validation.
    5. **COOLDOWN**: Prevents spamming the log for the same person.

### **Visual Feedback (Lines 1354-1373)**

```python
1360:             cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
```

* Draws the green/yellow boxes around faces.

---

## **Part 6: Threading & Cleanup**

```python
1407: if __name__ == '__main__':
1410:     flask_thread = threading.Thread(target=run_flask_app)
1411:     flask_thread.daemon = True
1412:     flask_thread.start()
1438:     run_face_recognition_loop()
```

* **`daemon = True`**: Important! This means "if the main program (Face Rec) dies, kill this thread (Flask) too." Prevents zombie processes.
* **Execution Order**:
    1. Start Web Server in background.
    2. Print the IP addresses.
    3. Start the Main Camera Loop (Blocking).

---

## **Why is this "State of the Art"?**

1. **Hybrid Architecture**: Combines synchronous (Camera) and asynchronous (Web) logic in one simplified file.
2. **Edge AI**: Runs modern ONNX models (YuNet/SFace) entirely locally without internet.
3. **RAG Integration**: The Chatbot isn't just a generic LLM; it "reads" your live logs before answering.
4. **Self-Healing**: The Lobby Logic automatically fixes logs if someone leaves without saying goodbye.
