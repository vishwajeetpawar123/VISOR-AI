import face_recognition
import cv2
import numpy as np
import os
import time
from datetime import datetime

# PHOTO ATTENDANCE MODE: Logs Entry/Exit + Saves Photo Evidence

# 1. Setup Video
video_capture = cv2.VideoCapture(0)
video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Load Haar Cascade
face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_detector = cv2.CascadeClassifier(face_cascade_path)

if face_detector.empty():
    print("Error: Could not load Haar Cascade XML.")
    exit()

# 2. Load Faces
known_face_encodings = []
known_face_names = []
faces_dir = "faces"

print(f"Loading faces from '{faces_dir}' folder...")
if os.path.exists(faces_dir):
    for filename in os.listdir(faces_dir):
        if filename.lower().endswith((".jpg", ".png", ".jpeg")):
            image_path = os.path.join(faces_dir, filename)
            try:
                image = face_recognition.load_image_file(image_path)
                encodings = face_recognition.face_encodings(image)
                if len(encodings) > 0:
                    known_face_encodings.append(encodings[0])
                    name = os.path.splitext(filename)[0]
                    known_face_names.append(name)
                    print(f" - Loaded: {name}")
            except Exception as e:
                print(f" - ERROR loading {filename}: {e}")
else:
    print(f"Warning: '{faces_dir}' folder not found.")

# 3. Setup Logging & Photos
log_file = "lobby_log.csv"
photos_dir = "attendance_photos"

if not os.path.exists(log_file):
    with open(log_file, "w") as f:
        f.write("Timestamp,Event,Name,PhotoPath\n")

if not os.path.exists(photos_dir):
    os.makedirs(photos_dir)

def log_event(event, name, frame=None):
    now_obj = datetime.now()
    now_str = now_obj.strftime("%Y-%m-%d %H:%M:%S")
    photo_filename = ""
    
    # If this is an ENTRY event, save a photo
    if event == "ENTERED" and frame is not None:
        # Create a safe filename
        safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '_')]).strip()
        timestamp_for_file = now_obj.strftime("%Y%m%d_%H%M%S")
        photo_filename = f"{photos_dir}/Attendance_{safe_name}_{timestamp_for_file}.jpg"
        
        # Draw timestamp on the photo itself for "hardcopy" proof
        evidence_frame = frame.copy()
        cv2.putText(evidence_frame, f"{now_str} - {name}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        cv2.imwrite(photo_filename, evidence_frame)
        print(f"SNAPSHOT SAVED: {photo_filename}")

    print(f"LOG: {event} - {name} at {now_str}")
    
    with open(log_file, "a") as f:
        f.write(f"{now_str},{event},{name},{photo_filename}\n")

# State tracking
# { name: timestamp_last_seen }
present_people = {}
EXIT_THRESHOLD = 3.0 # Seconds before we consider someone "Gone"

# To avoid spamming photos if detection flickers, we only log ENTER if they were GONE for > threshold
# This is handled naturally by the presence logic below.

print("Starting video... Press 'q' to quit.")

# Variables
face_names = []
process_this_frame = 0

while True:
    ret, frame = video_capture.read()
    if not ret:
        break

    # 1. Detect Faces (Haar)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rects = face_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    current_face_locations = []
    for (x, y, w, h) in rects:
        current_face_locations.append((y, x + w, y + h, x))

    # 2. Recognize Faces (Every 5 frames)
    # OPTIMIZATION: We only identify faces if we see them.
    if process_this_frame % 5 == 0:
        face_names = []
        if len(current_face_locations) > 0:
            rgb_frame = frame[:, :, ::-1]
            face_encodings = face_recognition.face_encodings(rgb_frame, current_face_locations)

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
                    # If they weren't here before, Log ENTRY and Take PHOTO
                    if name not in present_people:
                        log_event("ENTERED", name, frame)
                    
                    # Update their last seen time
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


    # Fill names for display
    while len(face_names) < len(current_face_locations):
        face_names.append("Checking...")
    
    # Display results
    for (top, right, bottom, left), name in zip(current_face_locations, face_names):
        color = (0, 255, 0)
        if name == "Unknown":
            color = (0, 0, 255)
        elif name == "Checking...":
            color = (255, 255, 0)

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

    cv2.imshow('Video', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video_capture.release()
cv2.destroyAllWindows()
