
import cv2
import face_recognition
import numpy as np
import os
import dlib

img_path = "faces/vaishnavi.jpg"

if not os.path.exists(img_path):
    print(f"File not found: {img_path}")
    exit(1)

print(f"Testing with {img_path}")

# Method 1: cv2
print("\n--- Method 1: OpenCV ---")
img_cv = cv2.imread(img_path)
if img_cv is None:
    print("cv2.imread failed")
else:
    print(f"Original Shape: {img_cv.shape}")
    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    img_rgb = np.ascontiguousarray(img_rgb, dtype=np.uint8)
    
    print(f"Processed Shape: {img_rgb.shape}")
    print(f"Dtype: {img_rgb.dtype}")
    print(f"Strides: {img_rgb.strides}")
    print(f"Flags:\n{img_rgb.flags}")

    try:
        print("Attempting face_encodings...")
        encs = face_recognition.face_encodings(img_rgb)
        print(f"Success! Found {len(encs)} faces.")
    except Exception as e:
        print(f"FAILED: {e}")

# Method 2: Standard face_recognition load
print("\n--- Method 2: face_recognition.load_image_file ---")
try:
    img_fr = face_recognition.load_image_file(img_path)
    print(f"Shape: {img_fr.shape}")
    print(f"Dtype: {img_fr.dtype}")
    print(f"Flags:\n{img_fr.flags}")
    
    print("Attempting face_encodings...")
    encs = face_recognition.face_encodings(img_fr)
    print(f"Success! Found {len(encs)} faces.")
except Exception as e:
    print(f"FAILED: {e}")

# Method 3: Direct dlib check
print("\n--- Method 3: Direct dlib detector ---")
detector = dlib.get_frontal_face_detector()
try:
    current_img = img_rgb # reuse from Method 1
    dets = detector(current_img, 1)
    print(f"Detector found {len(dets)} faces")
except Exception as e:
    print(f"Detector FAILED: {e}")
