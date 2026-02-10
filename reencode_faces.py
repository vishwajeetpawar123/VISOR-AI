import os
import cv2
import numpy as np
import pickle

FACES_DIR = "faces"
MODELS_DIR = "models"
ENCODINGS_FILE = "face_encodings_sface.pkl"

# Model paths
DETECTOR_PATH = os.path.join(MODELS_DIR, "face_detection_yunet_2023mar.onnx")
RECOGNIZER_PATH = os.path.join(MODELS_DIR, "face_recognition_sface_2021dec.onnx")

def main():
    if not os.path.exists(DETECTOR_PATH) or not os.path.exists(RECOGNIZER_PATH):
        print("❌ Models not found! Run 'download_models.py' first.")
        return

    # Initialize models
    detector = cv2.FaceDetectorYN.create(
        DETECTOR_PATH, "", (320, 320), 0.6, 0.3, 5000
    )
    recognizer = cv2.FaceRecognizerSF.create(RECOGNIZER_PATH, "")

    known_encodings = {}

    print(f"📂 Scanning '{FACES_DIR}' for faces...")
    
    if not os.path.exists(FACES_DIR):
        print(f"❌ '{FACES_DIR}' directory not found.")
        return

    count = 0
    for filename in os.listdir(FACES_DIR):
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue

        path = os.path.join(FACES_DIR, filename)
        name = os.path.splitext(filename)[0]

        # Read image
        img = cv2.imread(path)
        if img is None:
            print(f"⚠️ Could not read {filename}")
            continue

        # Resize for detection if too large (improves speed)
        h, w = img.shape[:2]
        detector.setInputSize((w, h))

        # Detect face
        has_face, faces = detector.detect(img)
        
        if has_face and faces is not None:
             # Get the first face (score, x, y, w, h, ...)
            face_box = faces[0]
            
            # Align and Crop
            aligned_face = recognizer.alignCrop(img, face_box)
            
            # Get Feature (Embedding)
            face_feature = recognizer.feature(aligned_face)
            
            # Clone feature to ensure it's clean
            face_feature = face_feature.copy()
            
            known_encodings[name] = face_feature
            print(f"✅ Encoded: {name}")
            count += 1
        else:
            print(f"⚠️ No face detected in {filename}")

    # Save to disk
    with open(ENCODINGS_FILE, 'wb') as f:
        pickle.dump(known_encodings, f)

    print(f"\n🎉 Finished! Saved {count} face encodings to '{ENCODINGS_FILE}'")

if __name__ == "__main__":
    main()
