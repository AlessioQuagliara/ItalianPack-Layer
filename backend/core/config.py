# core/config.py
from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

    # PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "postgresql://partflow:secret@localhost:5432/partflow")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File uploads (scontrini OCR)
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(os.path.dirname(__file__), "..", "uploads"))
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

    # Panthera ERP
    PANTHERA_BASE_URL = os.getenv("PANTHERA_BASE_URL", "")
    PANTHERA_API_KEY  = os.getenv("PANTHERA_API_KEY", "")

    # OCR
    OCR_ENGINE             = os.getenv("OCR_ENGINE", "tesseract")     # tesseract | google_vision
    GOOGLE_VISION_API_KEY  = os.getenv("GOOGLE_VISION_API_KEY", "")
    TESSERACT_CMD          = os.getenv("TESSERACT_CMD", "tesseract")  # path to binary
