#!/usr/bin/env python3
"""
CLI utility to enroll employee faces from a single official photo per employee using DeepFace ArcFace.
- Input: a folder of images either flat (employees/Name.jpg) or one image per subfolder (employees/Name/official.jpg)
- Output: a pickle file with a dict { name: embedding_vector }

Usage:
  python enroll_faces.py --photos "C:/path/to/employees" --output "C:/path/to/face_db.pkl"
If arguments are omitted, falls back to EMPLOYEE_PHOTOS_DIR and EMBEDDING_FILE from config.
"""

import argparse
import logging

import os
import cv2
import numpy as np
from deepface import DeepFace
from config import EMPLOYEE_PHOTOS_DIR, EMBEDDING_FILE, ARC_FACE_MODEL
import pickle


def main():
    parser = argparse.ArgumentParser(description="Enroll faces from single photos using ArcFace")
    parser.add_argument("--photos", type=str, default=EMPLOYEE_PHOTOS_DIR, help="Employees photos folder")
    parser.add_argument("--output", type=str, default=EMBEDDING_FILE, help="Output pickle path for embeddings")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # Build model once
    model = None  # DeepFace.represent will manage model internally

    def l2_normalize(v):
        v = np.asarray(v, dtype=np.float32).ravel()
        n = np.linalg.norm(v)
        return v if n == 0 else v / n

    def augment_image(img):
        h, w = img.shape[:2]
        aug = []
        # base
        aug.append(img)
        # brightness/contrast
        for alpha in (0.9, 1.1):  # contrast
            for beta in (-15, 15):  # brightness
                a = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
                aug.append(a)
        # small rotations
        for angle in (-7, -4, 4, 7):
            M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
            r = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            aug.append(r)
        return aug

    def one_strong_embedding(image_path: str):
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")
        images = augment_image(img)
        embs = []
        for im in images:
            try:
                rep = DeepFace.represent(
                    img_path=im,
                    model_name=ARC_FACE_MODEL,
                    enforce_detection=True,
                    detector_backend="opencv",
                    normalization="ArcFace"
                )
                if rep and isinstance(rep, list):
                    emb = rep[0].get("embedding")
                    if emb is not None:
                        embs.append(l2_normalize(emb))
            except Exception:
                continue
        if not embs:
            raise ValueError(f"No embeddings generated for: {image_path}")
        # Average and normalize
        avg = l2_normalize(np.mean(np.stack(embs, axis=0), axis=0))
        return avg

    face_db = {}
    # Walk photos folder (flat files or one image per subfolder)
    if os.path.isdir(args.photos):
        for entry in os.listdir(args.photos):
            path = os.path.join(args.photos, entry)
            if os.path.isdir(path):
                files = [f for f in os.listdir(path) if f.lower().endswith((".jpg",".jpeg",".png"))]
                if not files:
                    continue
                name = os.path.basename(path)
                emb = one_strong_embedding(os.path.join(path, files[0]))
                face_db[name] = emb
                logging.info(f"Enrolled (strong) {name} from {files[0]}")
            else:
                if entry.lower().endswith((".jpg",".jpeg",".png")):
                    name = os.path.splitext(entry)[0]
                    emb = one_strong_embedding(path)
                    face_db[name] = emb
                    logging.info(f"Enrolled (strong) {name} from {entry}")

    with open(args.output, "wb") as f:
        pickle.dump(face_db, f)
    logging.info(f"Enrollment completed successfully -> {args.output} ({len(face_db)} employees)")


if __name__ == "__main__":
    main()
