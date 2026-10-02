import os
from pathlib import Path
from dotenv import load_dotenv

# Load variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Application configuration settings."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'datalens-dev-secret-key-2026')
    DATABASE_PATH = BASE_DIR / 'datalens.db'
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    REPORTS_FOLDER = BASE_DIR / 'generated_reports'
    SAMPLE_DATA_FOLDER = BASE_DIR / 'sample_data'
    
    # 10 MB upload limit
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    
    # Google Gemini API Key
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
