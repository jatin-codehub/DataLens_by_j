import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Load variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Detect if running in Vercel or other serverless/read-only environment
IS_SERVERLESS = bool(os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))

if IS_SERVERLESS:
    DATA_DIR = Path('/tmp')
    os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'
else:
    DATA_DIR = BASE_DIR

class Config:
    """Application configuration settings for privacy-first temporary analysis."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'datalens-privacy-secret-key-2026')
    
    # Base and temporary directory management
    SAMPLE_DATA_FOLDER = BASE_DIR / 'sample_data'
    TEMP_DIR_ROOT = Path(tempfile.gettempdir()) / 'datalens_sessions'
    
    # Fallback paths for legacy test suites
    DATABASE_PATH = TEMP_DIR_ROOT / 'datalens.db'
    UPLOAD_FOLDER = TEMP_DIR_ROOT / 'uploads'
    REPORTS_FOLDER = TEMP_DIR_ROOT / 'reports'
    
    # 25 MB configurable upload limit (Rule 13 & 24)
    MAX_UPLOAD_MB = int(os.environ.get('MAX_UPLOAD_MB', 25))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    
    # Temporary Session TTL (minutes) - Rule 6 & 24
    SESSION_TTL_MINUTES = int(os.environ.get('SESSION_TTL_MINUTES', 30))
    
    # Abuse & Rate Limits per Temporary Session (Rule 24)
    MAX_AI_REQUESTS = int(os.environ.get('MAX_AI_REQUESTS', 15))
    MAX_ASK_REQUESTS = int(os.environ.get('MAX_ASK_REQUESTS', 30))
    
    # Google Gemini API Key
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')


