#!/usr/bin/env python3
"""
Face Recognition Agent Module
Handles facial recognition functionality
"""

import cv2
import pickle
import numpy as np
import time
import logging
from deepface import DeepFace
from config import EMBEDDING_FILE, SIMILARITY_THRESHOLD

class FaceRecognitionAgent:
    """Agent 3: Facial Recognition with Pre-initialized Camera"""
    
    def __init__(self):
        self.face_db = None
        self.load_face_database()
        # Pre-load face cascade for instant detection
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        # Pre-initialize camera for instant access
        self.cap = None
        self.camera_initialized = False
        # Avoid showing OpenCV window by default (prevents GUI-related crashes)
        self.show_camera_window = False
        self.initialize_camera()
    
    def initialize_camera(self):
        """Pre-initialize camera for instant access"""
        try:
            # Try default backend first
            self.cap = cv2.VideoCapture(0)
            # If not opened, try Windows DirectShow backend (often more reliable on Windows)
            if not self.cap or not self.cap.isOpened():
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)  # Smaller resolution for speed
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            self.cap.set(cv2.CAP_PROP_FPS, 15)  # Lower FPS for faster processing
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)  # Disable autofocus for speed
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Fixed exposure
            
            # Camera is ready when opened
            if self.cap and self.cap.isOpened():
                self.camera_initialized = True
                logging.info("📷 Camera pre-initialized successfully (isOpened=True)")
            else:
                self.camera_initialized = False
                logging.warning("📷 Camera initialization failed")
        except Exception as e:
            logging.error(f"📷 Camera initialization error: {e}")
            self.camera_initialized = False
        
    def load_face_database(self):
        """Load face database from pickle file"""
        try:
            with open(EMBEDDING_FILE, "rb") as f:
                self.face_db = pickle.load(f)
            logging.info(" Face database loaded successfully")
        except Exception as e:
            logging.error(f" Failed to load face database: {e}")
            self.face_db = {}
            
    def get_embedding(self, face_img):
        """Generate face embedding using DeepFace (Facenet512)."""
        try:
            # Let DeepFace handle resizing/normalization for Facenet512
            rep = DeepFace.represent(
                img_path=face_img,
                model_name="Facenet512",
                enforce_detection=False,
                detector_backend="opencv"
            )
            # DeepFace.represent returns a list of dicts; extract embedding
            if rep and isinstance(rep, list):
                first = rep[0]
                return first.get("embedding", None)
            return None
        except Exception as e:
            logging.error(f"Error generating embedding: {e}")
            return None
            
    def cosine_similarity(self, a, b):
        """Calculate cosine similarity between embeddings"""
        a, b = np.array(a), np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
    def identify_face(self, embedding):
        """Identify face from embedding using cosine similarity against database."""
        if embedding is None or not self.face_db:
            logging.info("No embedding or face database available")
            return "Unknown", 0.0

        best_match = "Unknown"
        best_score = -1.0

        for name, stored_embeddings in self.face_db.items():
            # stored_embeddings may be:
            # - a list of raw vectors
            # - a list of dicts with key 'embedding'
            # - a single dict or vector (older datasets)
            if stored_embeddings is None:
                continue

            candidates = []
            if isinstance(stored_embeddings, list):
                for item in stored_embeddings:
                    if isinstance(item, dict) and "embedding" in item:
                        candidates.append(item["embedding"])
                    else:
                        candidates.append(item)
            elif isinstance(stored_embeddings, dict) and "embedding" in stored_embeddings:
                candidates.append(stored_embeddings["embedding"])
            else:
                candidates.append(stored_embeddings)

            for ref in candidates:
                try:
                    score = self.cosine_similarity(embedding, ref)
                except Exception:
                    continue
                if score > best_score:
                    best_score = score
                    best_match = name

        logging.info(
            f"Best match: {best_match} (score: {best_score:.3f}, threshold: {SIMILARITY_THRESHOLD})"
        )

        if best_score >= SIMILARITY_THRESHOLD:
            logging.info(f"✅ Face recognized as: {best_match}")
            return best_match, best_score
        else:
            logging.info("❌ Face below threshold - will classify as Unknown only if a face is detected")
            return "Unknown", best_score
        
    def recognize_facye_from_camera(self):
        """Continuously monitor camera and recognize the largest visible face.

        Behavior:
        - Keep watching the camera until at least one face is detected.
        - If multiple faces are present, pick the one with the largest bounding box area.
        - Compare against the known database (Facenet512 embeddings).
        - Return a known name if similarity >= threshold.
        - Only return "Unknown" after a face was clearly detected and did not match.
        """
        logging.info("📷 Starting face recognition with pre-initialized camera...")

        # Use pre-initialized camera if available, otherwise initialize new one
        using_preinitialized = False
        if self.camera_initialized and self.cap is not None and self.cap.isOpened():
            cap = self.cap
            using_preinitialized = True
            logging.info("📷 Using pre-initialized camera (isOpened=True)")
        else:
            logging.info("📷 Initializing new camera...")
            cap = cv2.VideoCapture(0)
            if not cap or not cap.isOpened():
                # Fallback to DirectShow on Windows
                try:
                    cap.release()
                except Exception:
                    pass
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            cap.set(cv2.CAP_PROP_FPS, 15)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            using_preinitialized = False

        if not cap or not cap.isOpened():
            logging.warning("📷 Camera not opened (isOpened=False) - cannot start recognition")
            return "Unknown", 0.0

        # Warm-up frames
        for _ in range(5):
            ret, _ = cap.read()
            if ret:
                break
            time.sleep(0.03)

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    logging.warning("Failed to read camera frame")
                    time.sleep(0.02)
                    continue

                # Optionally show camera feed
                if self.show_camera_window:
                    try:
                        cv2.imshow("Face Recognition", frame)
                    except Exception as imshow_err:
                        logging.warning(f"OpenCV imshow error (disabling window): {imshow_err}")
                        self.show_camera_window = False

                # Use smaller grayscale for fast detection
                small_frame = cv2.resize(frame, (160, 120))
                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.2,
                    minNeighbors=3,
                    minSize=(20, 20)
                )

                if len(faces) == 0:
                    # No faces visible; keep watching
                    continue

                # Choose the largest face by area
                largest = None
                largest_area = -1
                for (x, y, w, h) in faces:
                    area = w * h
                    if area > largest_area:
                        largest_area = area
                        largest = (x, y, w, h)

                # Scale coordinates back to original frame size
                x, y, w, h = largest
                scale_x = frame.shape[1] / 160.0
                scale_y = frame.shape[0] / 120.0
                x = int(x * scale_x)
                y = int(y * scale_y)
                w = int(w * scale_x)
                h = int(h * scale_y)

                # Crop the largest face and compute embedding
                face_img = frame[y:y + h, x:x + w]
                if face_img.size == 0:
                    # Invalid crop; continue
                    continue

                embedding = self.get_embedding(face_img)
                if embedding is None:
                    # Could not extract embedding; continue watching
                    logging.info("Could not extract embedding; continuing to watch")
                    continue

                name, score = self.identify_face(embedding)

                # Draw rectangle and label if window is enabled
                if self.show_camera_window:
                    color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    cv2.putText(
                        frame,
                        f"{name} ({score:.2f})",
                        (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        color,
                        1,
                    )

                # Decision: Only return Unknown after a face is detected and no match found
                if name != "Unknown":
                    logging.info(f"✅ Recognized known face: {name} (score: {score:.2f})")
                    return name, score
                else:
                    logging.info(
                        f"❌ Detected face did not match any known embedding (score: {score:.2f}); classifying as Unknown"
                    )
                    return "Unknown", score

        except Exception as e:
            logging.exception(f"Camera error: {e}")
            return "Unknown", 0.0
        finally:
            if not using_preinitialized:
                try:
                    cap.release()
                except Exception:
                    pass
            if self.show_camera_window:
                try:
                    cv2.destroyAllWindows()
                except Exception:
                    pass
    
    def recognize_face_with_result_callback(self, result_callback):
        """Recognize face and call callback with result - for threaded operation"""
        name, score = self.recognize_facye_from_camera()
        result_callback(name, score)
    
    def cleanup_camera(self):
        """Clean up pre-initialized camera"""
        if self.camera_initialized and self.cap is not None:
            self.cap.release()
            self.camera_initialized = False
            logging.info("📷 Pre-initialized camera cleaned up")
