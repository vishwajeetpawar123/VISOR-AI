import os
import cv2
import numpy as np
import time
from datetime import datetime
import multiprocessing
import logging
from flask import Flask, render_template_string, jsonify, send_from_directory, Response
import socket

# ==========================================
# CONFIGURATION
# ==========================================
FACES_DIR = "faces"
PHOTOS_DIR = "attendance_photos"
LOG_FILE = "lobby_log.csv"
EXIT_THRESHOLD = 3.0  # Seconds before considering someone "Gone"

# HTML Template embedded directly so no separate file is needed
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Attendance Live Stream</title>
    <style>
        :root {
            --bg-color: #0d1117;
            --card-bg: #161b22;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --accent: #58a6ff;
            --border: #30363d;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0;
            padding: 20px;
        }
        header {
            border-bottom: 1px solid var(--border);
            padding-bottom: 20px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 {
            margin: 0;
            font-size: 1.5rem;
            color: var(--accent);
        }
        .status {
            font-size: 0.9rem;
            color: var(--text-secondary);
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
        }
        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 6px;
            overflow: hidden;
            transition: transform 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            border-color: var(--accent);
        }
        .card img {
            width: 100%;
            height: auto;
            display: block;
            border-bottom: 1px solid var(--border);
        }
        .card-body {
            padding: 15px;
        }
        .card-title {
            font-weight: 600;
            margin-bottom: 5px;
            color: var(--text-primary);
        }
        .card-time {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }
        .empty-state {
            text-align: center;
            padding: 50px;
            color: var(--text-secondary);
            font-style: italic;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .new-item {
            animation: fadeIn 0.5s ease-out;
        }
    </style>
</head>
<body>

<header>
    <h1>📸 Attendance Live Stream</h1>
    <div class="status">Auto-refreshing every 3s</div>
</header>

<div id="photo-grid" class="grid">
    <!-- Photos will be injected here -->
</div>

<script>
    async function fetchPhotos() {
        try {
            const response = await fetch('/api/photos');
            const photos = await response.json();
            
            const grid = document.getElementById('photo-grid');
            
            if (photos.length === 0) {
                grid.innerHTML = '<div class="empty-state">No attendance records found yet.</div>';
                return;
            }

            const currentPhotosKey = photos.map(p => p.filename).join(',');
            if (grid.dataset.key === currentPhotosKey) {
                return; // No changes
            }
            grid.dataset.key = currentPhotosKey;

            grid.innerHTML = ''; // Clear

            photos.forEach(photo => {
                const card = document.createElement('div');
                card.className = 'card new-item';
                
                card.innerHTML = `
                    <img src="${photo.url}" alt="${photo.name}" loading="lazy">
                    <div class="card-body">
                        <div class="card-title">${photo.name}</div>
                        <div class="card-time">${photo.timestamp}</div>
                    </div>
                `;
                grid.appendChild(card);
            });

        } catch (error) {
            console.error('Error fetching photos:', error);
        }
    }

    // Initial load
    fetchPhotos();

    // Poll every 3 seconds
    setInterval(fetchPhotos, 3000);

</script>

</body>
</html>
"""

# ==========================================
# WEB SERVER SETUP
# ==========================================
app = Flask(__name__)
# Suppress Flask server logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/photos')
def get_photos():
    if not os.path.exists(PHOTOS_DIR):
        return jsonify([])

    files = [f for f in os.listdir(PHOTOS_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    # Sort by modification time (newest first)
    files.sort(key=lambda x: os.path.getmtime(os.path.join(PHOTOS_DIR, x)), reverse=True)
    
    photo_data = []
    for filename in files:
        # Attendance_Name_YYYYMMDD_HHMMSS.jpg
        parts = filename.split('_')
        display_name = "Unknown"
        
        if len(parts) >= 3 and parts[0] == "Attendance":
            if len(parts) >= 4:
                # Name might separate with spaces which became separate parts if original name had underscores
                # But our save logic uses underscores replacer? 
                # Our save logic: safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '_')]).strip()
                # Actually, let's just grab the middle chunk.
                name_parts = parts[1:-2]
                display_name = " ".join(name_parts)
            else:
                display_name = parts[1]
        
        filepath = os.path.join(PHOTOS_DIR, filename)
        mod_time = os.path.getmtime(filepath)
        dt = datetime.fromtimestamp(mod_time)
        timestamp_display = dt.strftime("%Y-%m-%d %H:%M:%S")

        photo_data.append({
            'filename': filename,
            'name': display_name,
            'timestamp': timestamp_display,
            'url': f'/photos/{filename}'
        })
        
    return jsonify(photo_data)

@app.route('/photos/<path:filename>')
def serve_photo(filename):
    return send_from_directory(os.path.abspath(PHOTOS_DIR), filename)

def run_flask_app():
    # Helper to find IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    
    print("-" * 50)
    print(f"WEB VIEWER STARTED")
    print(f" * Local URL:   http://localhost:5000")
    print(f" * Mobile URL:  http://{IP}:5000")
    print("-" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# ==========================================
# FACE RECOGNITION SYSTEM
# ==========================================
def log_event(event, name, frame=None):
    now_obj = datetime.now()
    now_str = now_obj.strftime("%Y-%m-%d %H:%M:%S")
    photo_filename = ""
    
    # If this is an ENTRY event, save a photo
    if event == "ENTERED" and frame is not None:
        # Create a safe filename
        safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '_')]).strip()
        timestamp_for_file = now_obj.strftime("%Y%m%d_%H%M%S")
        photo_filename = f"{PHOTOS_DIR}/Attendance_{safe_name}_{timestamp_for_file}.jpg"
        
        # Draw timestamp on the photo itself for "hardcopy" proof
        evidence_frame = frame.copy()
        cv2.putText(evidence_frame, f"{now_str} - {name}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        cv2.imwrite(photo_filename, evidence_frame)
        print(f"SNAPSHOT SAVED: {photo_filename}")

    print(f"LOG: {event} - {name} at {now_str}")
    
    with open(LOG_FILE, "a") as f:
        f.write(f"{now_str},{event},{name},{photo_filename}\n")

def run_face_recognition_loop():
    # 1. Setup Directories
    if not os.path.exists(PHOTOS_DIR):
        os.makedirs(PHOTOS_DIR)
    
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("Timestamp,Event,Name,PhotoPath\n")

    # 2. Setup Video
    video_capture = cv2.VideoCapture(0)
    if not video_capture.isOpened():
        print("ERROR: Could not access the camera.")
        return

    video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # Load Haar Cascade
    face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_detector = cv2.CascadeClassifier(face_cascade_path)

    # 3. Load Faces
    # Lazy import to save RAM in the Flask process
    import face_recognition

    known_face_encodings = []
    known_face_names = []
    
    print(f"Loading faces from '{FACES_DIR}' folder...")
    if os.path.exists(FACES_DIR):
        for filename in os.listdir(FACES_DIR):
            if filename.lower().endswith((".jpg", ".png", ".jpeg")):
                image_path = os.path.join(FACES_DIR, filename)
                try:
                    # Use OpenCV to load to ensure consistency
                    image = cv2.imread(image_path)
                    if image is None:
                        print(f" - WARNING: Could not load {filename} (cv2.imread returned None)")
                        continue
                    
                    # Convert BGR to RGB
                    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    
                    # Force uint8 and contiguous
                    image_rgb = np.ascontiguousarray(image_rgb, dtype=np.uint8)
                    
                    encodings = face_recognition.face_encodings(image_rgb)
                    if len(encodings) > 0:
                        known_face_encodings.append(encodings[0])
                        name = os.path.splitext(filename)[0]
                        known_face_names.append(name)
                        print(f" - Loaded: {name}")
                    else:
                        print(f" - WARNING: No face found in {filename}")
                except Exception as e:
                    print(f" - ERROR loading {filename}: {e}")
    else:
        print(f"Warning: '{FACES_DIR}' folder not found.")

    # State tracking
    present_people = {} # { name: timestamp_last_seen }
    
    print("Starting video... Press 'q' to quit. Press 's' to toggle Server.")

    face_names = []
    current_face_locations = []
    process_this_frame = 0
    
    server_process = None

    while True:
        ret, frame = video_capture.read()
        if not ret:
            break

        # Resize frame of video to 1/4 size for faster face recognition processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Process every 5th frame to save CPU
        if process_this_frame % 5 == 0:
            # 1. Detect Faces (Haar) on SMALL frame
            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            # Adjust minSize for smaller frame
            rects = face_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(10, 10))
            
            current_face_locations = []
            for (x, y, w, h) in rects:
                # face_recognition expects (top, right, bottom, left)
                current_face_locations.append((y, x + w, y + h, x))

            # 2. Recognize Faces
            face_names = []
            if len(current_face_locations) > 0:
                # Convert BGR to RGB
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                
                if rgb_small_frame.shape[2] == 4:
                     rgb_small_frame = cv2.cvtColor(rgb_small_frame, cv2.COLOR_RGBA2RGB)
                
                # FORCE uint8 and contiguous
                rgb_small_frame = np.ascontiguousarray(rgb_small_frame, dtype=np.uint8)
                
                # Pass small frame and small locations
                face_encodings = face_recognition.face_encodings(rgb_small_frame, current_face_locations)

                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                    name = "Unknown"

                    if len(known_face_encodings) > 0:
                        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            name = known_face_names[best_match_index]

                    face_names.append(name)
                    
                    # --- LOGGING LOGIC ---
                    now = time.time()
                    if name != "Unknown":
                        if name not in present_people:
                            log_event("ENTERED", name, frame)
                        present_people[name] = now

        process_this_frame += 1

        # --- CHECK EXITS ---
        now = time.time()
        people_to_remove = []
        for name, last_seen in present_people.items():
            if now - last_seen > EXIT_THRESHOLD:
                log_event("EXITED", name)
                people_to_remove.append(name)
        
        for name in people_to_remove:
            del present_people[name]

        # Display results
        for (top, right, bottom, left), name in zip(current_face_locations, face_names):
            # Scale up by 4 for display
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            color = (0, 255, 0)
            if name == "Unknown":
                color = (0, 0, 255)

            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

        # Show "Lobby Status"
        status_y = 30
        cv2.putText(frame, "LOBBY STATUS:", (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        for name in present_people:
            status_y += 30
            cv2.putText(frame, f"- {name}", (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Show Server Status
        server_status = "ON" if (server_process and server_process.is_alive()) else "OFF"
        cv2.putText(frame, f"Server: {server_status} (Press 's')", (10, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        cv2.imshow('Attendance System (Press q to quit)', frame)

        key = cv2.waitKey(30) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            if server_process and server_process.is_alive():
                print("Stopping Web Server...")
                server_process.terminate()
                server_process.join()
                server_process = None
            else:
                print("Starting Web Server...")
                server_process = multiprocessing.Process(target=run_flask_app)
                server_process.start()

    if server_process and server_process.is_alive():
        server_process.terminate()

    video_capture.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    multiprocessing.freeze_support()
    run_face_recognition_loop()
