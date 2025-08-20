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
from config import (
    EMBEDDING_FILE, SIMILARITY_THRESHOLD, EMPLOYEE_PHOTOS_DIR, ARC_FACE_MODEL,
    FRAME_COUNT, CONSECUTIVE_REQUIRED, VAR_LAPLACIAN_MIN, MIN_FACE_RATIO,
    BRIGHTNESS_MIN, BRIGHTNESS_MAX, RECOG_TIME_LIMIT_SECS, EARLY_ACCEPT_MARGIN
)

import os

class FaceRecognitionAgent:
    """Agent 3: Facial Recognition with Pre-initialized Camera"""
    
    def __init__(self):
        self.face_db = None
        # Build ArcFace model once and reuse
        try:
            self.model = DeepFace.build_model(ARC_FACE_MODEL)
            logging.info(f"🔧 Loaded ArcFace model once for reuse")
        except Exception as e:
            logging.error(f"Failed to build ArcFace model: {e}")
            self.model = None
        self.load_face_database()
        self._build_embedding_matrix()
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
            # Try different camera backends on Windows
            backends = [
                (0, cv2.CAP_DSHOW),  # DirectShow (most reliable on Windows)
                (0, cv2.CAP_MSMF),   # Media Foundation
                (0, cv2.CAP_ANY),    # Auto-detect
            ]
            
            for camera_index, backend in backends:
                try:
                    if self.cap:
                        self.cap.release()
                    
                    self.cap = cv2.VideoCapture(camera_index, backend)
                    
                    # Set camera properties for better performance
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    self.cap.set(cv2.CAP_PROP_FPS, 30)
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                    self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                    
                    # Test if camera is working
                    if self.cap.isOpened():
                        ret, test_frame = self.cap.read()
                        if ret and test_frame is not None:
                            self.camera_initialized = True
                            logging.info(f"📷 Camera initialized successfully with backend {backend}")
                            return
                        else:
                            logging.warning(f"📷 Camera opened but can't read frames with backend {backend}")
                            self.cap.release()
                    else:
                        logging.warning(f"📷 Failed to open camera with backend {backend}")
                        
                except Exception as e:
                    logging.warning(f"📷 Camera initialization failed with backend {backend}: {e}")
                    if self.cap:
                        self.cap.release()
            
            # If all backends failed, try one more time with default settings
            try:
                self.cap = cv2.VideoCapture(0)
                if self.cap.isOpened():
                    ret, test_frame = self.cap.read()
                    if ret and test_frame is not None:
                        self.camera_initialized = True
                        logging.info("📷 Camera initialized with default settings")
                        return
            except Exception as e:
                logging.error(f"📷 Final camera attempt failed: {e}")
                
            self.camera_initialized = False
            logging.error("📷 All camera initialization attempts failed")
            
        except Exception as e:
            logging.error(f"📷 Camera initialization error: {e}")
            self.camera_initialized = False
        
    def load_face_database(self):
        """Load face database from pickle file"""
        try:
            with open(EMBEDDING_FILE, "rb") as f:
                self.face_db = pickle.load(f)
            logging.info(" Face database loaded successfully")
        except Exception:
            logging.warning(" No pickle face DB found; will build from EMPLOYEE_PHOTOS_DIR if available")
            self.face_db = {}
            try:
                self.enroll_all_from_folder(EMPLOYEE_PHOTOS_DIR)
                self.save_face_database()
            except Exception as e2:
                logging.error(f" Failed to build face DB from photos: {e2}")

    def _build_embedding_matrix(self):
        """Precompute names list and normalized embedding matrix for fast cosine compare."""
        self.names_list = []
        self.embedding_matrix = None
        try:
            if not self.face_db:
                return
            names = []
            vecs = []
            for name, emb in self.face_db.items():
                v = np.asarray(emb, dtype=np.float32).ravel()
                if v.size < 128:
                    continue
                v = self._l2_normalize(v)
                names.append(name)
                vecs.append(v)
            if vecs:
                self.names_list = names
                self.embedding_matrix = np.stack(vecs, axis=0)  # (N, D) L2-normalized
                logging.info(f"📦 Cached {len(self.names_list)} embeddings for fast compare")
        except Exception as e:
            logging.warning(f"Failed to build embedding matrix: {e}")
            
    @staticmethod
    def _l2_normalize(vec):
        v = np.asarray(vec, dtype=np.float32).ravel()
        n = np.linalg.norm(v)
        if n <= 1e-8:
            return v
        return v / n

    def get_embedding(self, face_img):
        """Generate face embedding using DeepFace ArcFace with more permissive detection."""
        try:
            # Try with enforce_detection=False first (more permissive)
            rep = DeepFace.represent(
                img_path=face_img,
                model_name=ARC_FACE_MODEL,
                enforce_detection=False,  # More permissive
                detector_backend="opencv",
                normalization="ArcFace"
            )
            # DeepFace.represent returns a list of dicts; extract embedding
            if rep and isinstance(rep, list):
                first = rep[0]
                emb = first.get("embedding", None)
                if emb is None:
                    return None
                logging.info(f"✅ Successfully extracted 512D embedding (length: {len(emb)})")
                return self._l2_normalize(emb)
            return None
        except Exception as e:
            logging.error(f"Error generating embedding: {e}")
            return None
            
    def cosine_similarity(self, a, b):
        """Calculate cosine similarity between embeddings as a scalar float."""
        a = np.asarray(a, dtype=np.float32).ravel()
        b = np.asarray(b, dtype=np.float32).ravel()
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0.0:
            return -1.0
        return float(np.dot(a, b) / denom)
        
    def identify_face(self, embedding):
        """Identify face from embedding using cosine similarity against database."""
        if embedding is None or not self.face_db:
            logging.info("No embedding or face database available")
            return "Unknown", 0.0

        best_match = "Unknown"
        best_score = -1.0
        per_name_best = {}

        # Determine live embedding length for compatibility checks
        live_len = len(np.asarray(embedding).ravel())


        def _is_number(x):
            return isinstance(x, (int, float, np.integer, np.floating))

        def _is_numeric_vector(obj):
            if isinstance(obj, (list, tuple)) and len(obj) > 8:
                # assume embedding-length vector if many numeric elements
                head = obj[:16]
                return all(_is_number(v) for v in head)
            return False

        for name, stored_embeddings in self.face_db.items():
            # stored_embeddings may be:
            # - a list of raw vectors
            # - a list of dicts with key 'embedding'
            # - a single dict or vector (older datasets)
            if stored_embeddings is None:
                continue

            candidates = []
            if isinstance(stored_embeddings, list):
                # If it's a vector (list of numbers), treat as single embedding
                if _is_numeric_vector(stored_embeddings):
                    candidates.append(stored_embeddings)
                else:
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
                    ref_vec = np.asarray(ref).ravel()
                    if ref_vec.size == 0 or np.linalg.norm(ref_vec) == 0.0:
                        continue
                    if ref_vec.size != live_len:
                        logging.warning(f"Embedding length mismatch for {name}: live={live_len}, ref={ref_vec.size} (skip)")
                        continue
                    # L2 normalize stored vector as well
                    ref_vec = self._l2_normalize(ref_vec)
                    score = self.cosine_similarity(embedding, ref_vec)
                except Exception:
                    continue
                if score > best_score:
                    best_score = score
                    best_match = name
                # track per-name best
                existing = per_name_best.get(name, -1.0)
                if score > existing:
                    per_name_best[name] = score

        # Log detailed confidence scores for each employee
        logging.info("🔍 Detailed confidence scores for each employee:")
        if per_name_best:
            sorted_scores = sorted(per_name_best.items(), key=lambda x: x[1], reverse=True)
            logging.info(f"📊 Live face compared against {len(sorted_scores)} stored embeddings:")
            for i, (name, score) in enumerate(sorted_scores, 1):
                status = "✅ RECOGNIZED" if score >= SIMILARITY_THRESHOLD else "❌ BELOW THRESHOLD"
                if i == 1:
                    logging.info(f"   🥇 CLOSEST MATCH: {name} (score: {score:.4f}) {status}")
                else:
                    logging.info(f"   {i}. {name}: {score:.4f} {status}")
            
            # Show the gap between best and second best
            if len(sorted_scores) > 1:
                best_score = sorted_scores[0][1]
                second_best_score = sorted_scores[1][1]
                gap = best_score - second_best_score
                logging.info(f"📈 Confidence gap: {sorted_scores[0][0]} leads by {gap:.4f} over {sorted_scores[1][0]}")
        else:
            logging.info("   No valid embeddings found for comparison")
        
        # Log top-3 similar names for debugging and compute early-accept gap
        second_best = -1.0
        if per_name_best:
            top = sorted(per_name_best.items(), key=lambda x: x[1], reverse=True)
            top3 = top[:3]
            top_str = ", ".join([f"{n}:{s:.3f}" for n, s in top3])
            logging.info(f"Similarity top matches -> {top_str}")
            if len(top) > 1:
                second_best = top[1][1]
        logging.info(f"Best match: {best_match} (score: {best_score:.3f}, threshold: {SIMILARITY_THRESHOLD})")

        return best_match, best_score, second_best

        # Strict decision by threshold only; tune threshold in .env
        if best_score >= SIMILARITY_THRESHOLD:
            logging.info(f"✅ Face recognized as: {best_match}")
            return best_match, best_score
        else:
            logging.info("❌ Face below threshold - will classify as Unknown only if a face is detected")
            return "Unknown", best_score

    # Enrollment API: one official photo per employee
    def enroll_employee(self, name: str, image_path: str):
        """Enroll a single official photo for an employee -> store one embedding."""
        try:
            rep = DeepFace.represent(
                img_path=image_path,
                model_name=ARC_FACE_MODEL,
                enforce_detection=False,  # More permissive for enrollment
                detector_backend="opencv",
                normalization="ArcFace"
            )
            if not rep:
                raise ValueError("No representation returned")
            emb = rep[0].get("embedding")
            if not emb:
                raise ValueError("No embedding in representation")
            self.face_db[name] = emb
            logging.info(f"✅ Enrolled {name} from {image_path} (embedding length: {len(emb)})")
            return True
        except Exception as e:
            logging.error(f"Failed to enroll {name} from {image_path}: {e}")
            return False

    def enroll_all_from_folder(self, folder_path: str):
        """Enroll all employees from a folder: one image per employee (filename or subfolder name as label)."""
        if not os.path.isdir(folder_path):
            logging.warning(f"Employee photos folder not found: {folder_path}")
            return
        for entry in os.listdir(folder_path):
            path = os.path.join(folder_path, entry)
            if os.path.isdir(path):
                # If using subfolders per employee with one image inside
                files = [f for f in os.listdir(path) if f.lower().endswith((".jpg",".jpeg",".png"))]
                if files:
                    name = os.path.basename(path)
                    self.enroll_employee(name, os.path.join(path, files[0]))
            else:
                # If using flat folder: filename without extension is name
                if entry.lower().endswith((".jpg",".jpeg",".png")):
                    name = os.path.splitext(entry)[0]
                    self.enroll_employee(name, path)

    def save_face_database(self, path: str | None = None):
        target_path = path or EMBEDDING_FILE
        try:
            with open(target_path, "wb") as f:
                pickle.dump(self.face_db, f)
            logging.info(f"Saved face DB embeddings to pickle: {target_path}")
        except Exception as e:
            logging.error(f"Failed to save face DB to {target_path}: {e}")
        
    def recognize_facye_from_camera(self):
        """Recognize with immediate decision: no liveness check, direct recognition."""
        logging.info("📷 Starting face recognition...")

        # Use pre-initialized camera if available, otherwise initialize new one
        using_preinitialized = False
        if self.camera_initialized and self.cap is not None and self.cap.isOpened():
            cap = self.cap
            using_preinitialized = True
            logging.info("📷 Using pre-initialized camera")
        else:
            logging.info("📷 Initializing new camera for recognition...")
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Try DirectShow first
            if not cap.isOpened():
                cap = cv2.VideoCapture(0)  # Fallback to default
            if not cap.isOpened():
                logging.error("📷 Failed to open camera")
                return "Unknown", 0.0

        try:
            # Warm up camera and test it's working
            warmup_frames = 0
            for _ in range(10):
                ret, frame = cap.read()
                if ret and frame is not None:
                    warmup_frames += 1
                time.sleep(0.05)
            
            if warmup_frames < 3:
                logging.warning(f"📷 Camera warmup failed - only {warmup_frames} good frames")
                if using_preinitialized:
                    # Reinitialize camera if pre-initialized one is having issues
                    logging.info("📷 Reinitializing camera due to poor performance...")
                    self.cleanup_camera()
                    self.initialize_camera()
                    if self.camera_initialized and self.cap and self.cap.isOpened():
                        cap = self.cap
                        using_preinitialized = True
                        logging.info("📷 Camera reinitialized successfully")
                    else:
                        logging.error("📷 Camera reinitialization failed")
                        return "Unknown", 0.0

            # Single frame evaluation with liveness-first approach
            max_attempts = 15  # Increased attempts for better chances
            consecutive_failures = 0
            
            for attempt in range(max_attempts):
                ret, frame = cap.read()
                if not ret or frame is None:
                    consecutive_failures += 1
                    logging.warning(f"Failed to read camera frame (attempt {attempt + 1}, consecutive failures: {consecutive_failures})")
                    if consecutive_failures >= 5:
                        logging.error("📷 Too many consecutive camera failures")
                        return "Unknown", 0.0
                    time.sleep(0.02)
                    continue
                
                consecutive_failures = 0  # Reset on successful frame

                # Resize for faster processing
                small_frame = cv2.resize(frame, (320, 240))
                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)

                # Detect faces - more sensitive parameters for photos/videos
                faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.05, minNeighbors=3, minSize=(20, 20)
                )

                if len(faces) == 0:
                    logging.info("No face detected in frame")
                    continue
                else:
                    logging.info(f"Detected {len(faces)} face(s) in frame")

                # Quality checks
                largest = None
                largest_area = 0
                for (x, y, w, h) in faces:
                    area = w * h
                    if area > largest_area:
                        largest_area = area
                        largest = (x, y, w, h)

                # Scale coordinates back to original frame size
                x, y, w, h = largest
                scale_x = frame.shape[1] / 320.0
                scale_y = frame.shape[0] / 240.0
                x = int(x * scale_x)
                y = int(y * scale_y)
                w = int(w * scale_x)
                h = int(h * scale_y)

                # Face size gating
                face_area = w * h
                frame_area = frame.shape[0] * frame.shape[1]
                if face_area / frame_area < MIN_FACE_RATIO:
                    logging.info("Face too small in frame")
                    continue

                # Quality checks: blur and brightness
                face_img = frame[y:y + h, x:x + w]
                if face_img.size == 0:
                    continue

                gray_face = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
                
                # Blur check
                laplacian_var = cv2.Laplacian(gray_face, cv2.CV_64F).var()
                if laplacian_var < VAR_LAPLACIAN_MIN:
                    logging.info(f"Face too blurry (var: {laplacian_var:.1f}, min required: {VAR_LAPLACIAN_MIN})")
                    continue

                # Brightness check
                brightness = np.mean(gray_face)
                if brightness < BRIGHTNESS_MIN or brightness > BRIGHTNESS_MAX:
                    logging.info(f"Face brightness out of range ({brightness:.1f}, required: {BRIGHTNESS_MIN}-{BRIGHTNESS_MAX})")
                    continue

                # All quality checks passed
                logging.info(f"✅ Face quality checks passed - blur: {laplacian_var:.1f}, brightness: {brightness:.1f}, size: {face_area}")

                # Proceed directly to ArcFace recognition (no liveness check)
                logging.info("🔍 Extracting 512D ArcFace embedding from live face...")
                embedding = self.get_embedding(face_img)
                if embedding is None:
                    logging.info("Could not extract embedding")
                    continue

                # Get recognition result
                name, score, second_best = self.identify_face(embedding)
                logging.info(f"🎯 Final recognition result: {name} (score: {score:.4f}, threshold: {SIMILARITY_THRESHOLD})")

                # IMMEDIATE DECISION LOGIC:
                # If confidence is high enough, recognize immediately
                if name != "Unknown" and score >= SIMILARITY_THRESHOLD:
                    logging.info(f"✅ High confidence match found: {name} (score: {score:.3f}). Recognizing immediately.")
                    return name, score
                
                # If confidence is too low, classify as Unknown immediately
                elif score < SIMILARITY_THRESHOLD:
                    logging.info(f"❌ Low confidence score ({score:.3f} < {SIMILARITY_THRESHOLD}). Classifying as Unknown immediately.")
                    return "Unknown", 0.0

                # If we get here, try next frame
                logging.info(f"Attempt {attempt + 1}/{max_attempts}: Face detected but processing incomplete")

            # If we've tried all attempts without a clear decision, classify as Unknown
            logging.info(f"❌ No clear recognition after {max_attempts} attempts. Classifying as Unknown.")
            return "Unknown", 0.0

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
