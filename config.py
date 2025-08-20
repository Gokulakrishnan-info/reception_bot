#!/usr/bin/env python3
"""
Configuration file for Modular AI Bot
Contains all constants, settings, and database configurations
"""

import logging
import os
from sqlalchemy import create_engine

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Logging setup
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("ai_reception_bot.log", encoding='utf-8'), 
        logging.StreamHandler()
    ]
)

# Configuration
EMBEDDING_FILE = os.getenv("EMBEDDING_FILE", r"C:\Users\Gokulakrishnan\Documents\Python_Learnings\CAM_AI_ASSISTANT\Modular_AI_Bot\face_db_arcface.pkl")
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.30"))  # Lowered ArcFace threshold for easier recognition
EMPLOYEE_PHOTOS_DIR = os.getenv("EMPLOYEE_PHOTOS_DIR", r"C:\Users\Gokulakrishnan\Documents\Python_Learnings\CAM_AI_ASSISTANT\Modular_AI_Bot\employee_photos")
ARC_FACE_MODEL = os.getenv("ARC_FACE_MODEL", "ArcFace")
WAKE_WORD = "jarvis"
FOLLOW_UP_PROMPT = os.getenv("FOLLOW_UP_PROMPT", "How else can I help you?")

# Recognition tuning (env-overridable)
FRAME_COUNT = int(os.getenv("RECOG_FRAME_COUNT", "16"))              # max frames to evaluate per attempt
CONSECUTIVE_REQUIRED = int(os.getenv("RECOG_CONSECUTIVE", "1"))       # frames required above threshold for accept
VAR_LAPLACIAN_MIN = float(os.getenv("RECOG_FOCUS_MIN", "10.0"))       # focus measure threshold (blur filter) - lowered for photos/videos
MIN_FACE_RATIO = float(os.getenv("RECOG_MIN_FACE_RATIO", "0.04"))      # min face area ratio of frame
BRIGHTNESS_MIN = float(os.getenv("RECOG_BRIGHTNESS_MIN", "10.0"))     # gray mean lower bound - very permissive for photos/videos
BRIGHTNESS_MAX = float(os.getenv("RECOG_BRIGHTNESS_MAX", "230.0"))    # gray mean upper bound - more permissive
RECOG_TIME_LIMIT_SECS = float(os.getenv("RECOG_TIME_LIMIT_SECS", "2.5"))  # hard cap per recognition attempt
EARLY_ACCEPT_MARGIN = float(os.getenv("RECOG_EARLY_ACCEPT_MARGIN", "0.10"))  # accept immediately if top-second >= margin

# AWS Bedrock Configuration
AWS_REGION = "us-east-1"  # Change to your preferred region
# Use Nova Lite for text generation (more reliable for general questions)
BEDROCK_MODEL_ID = "amazon.nova-lite-v1:0"
BEDROCK_TEXT_MODEL_ID = "amazon.nova-lite-v1:0"
MODEL_IS_SONIC = False  # Nova Lite is not a Sonic model
# Set to False if connection test causes issues
TEST_BEDROCK_ON_STARTUP = False

# Database configuration (env first, fallback to previous DSN)
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT", "3306")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")

if all([db_host, db_port, db_name, db_user, db_password]):
    dsn = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
else:
    dsn = "mysql+pymysql://root:Gokul%4011@localhost:3306/Employee"

DB_ENGINE = create_engine(
    dsn,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)
BACKUP_CSV = r"C:\Users\Gokulakrishnan\Documents\Python_Learnings\CAM_AI_ASSISTANT\full_employees_backup.csv"
ATTENDANCE_XLSX = r"C:\Users\Gokulakrishnan\Documents\Python_Learnings\CAM_AI_ASSISTANT\Avatar_Bot\EXCEL_DETAILS\EMPLOYEE_DETAILS.xlsx"

# Employee lookup configuration
field_map = {
    "joining date": "join_date",
    "Joining Date": "join_date",
    "Join Date": "join_date",
    "joining_date": "join_date",
    "join date": "join_date",
    "date of joining": "join_date",
    "hire date": "join_date",
    "salary": "salary",
    "email": "email",
    "position": "position",
    "department": "department"
}
allowed_fields = list(set(field_map.values()))

# Log configuration info
logging.info(
    f"Bedrock configured: model={BEDROCK_MODEL_ID} (sonic={MODEL_IS_SONIC}); TTS=Amazon Polly"
)
