import os
import time
import shutil
import secrets
import tempfile
import threading
from pathlib import Path
from config import Config

# Thread-safe in-memory session registry
_SESSIONS = {}
_LOCK = threading.Lock()

def _get_ttl_seconds():
    """Retrieve session TTL in seconds from Config."""
    return Config.SESSION_TTL_MINUTES * 60

def generate_secure_session_id():
    """Generate a cryptographically secure random session ID (never predictable)."""
    return secrets.token_urlsafe(24)

def cleanup_expired_sessions():
    """Sweep and remove all temporary directories and metadata for expired sessions."""
    now = time.time()
    ttl = _get_ttl_seconds()
    expired_ids = []

    with _LOCK:
        for sid, sess in _SESSIONS.items():
            if now - sess.get('last_active', sess.get('created_at', 0)) > ttl:
                expired_ids.append(sid)

    for sid in expired_ids:
        clear_session(sid)

def create_session(filename, file_type, df, temp_dir=None, file_path=None, summary=None, quality=None):
    """
    Create a new temporary session with isolated temporary directory and in-memory cache.
    Does NOT write to permanent storage or a database.
    """
    cleanup_expired_sessions()
    session_id = generate_secure_session_id()

    # Create an isolated temporary directory if not provided
    if not temp_dir:
        os.makedirs(Config.TEMP_DIR_ROOT, exist_ok=True)
        temp_dir = tempfile.mkdtemp(prefix=f"dl_{session_id[:8]}_", dir=str(Config.TEMP_DIR_ROOT))

    now = time.time()
    session_data = {
        "session_id": session_id,
        "filename": filename,
        "file_type": file_type.lower(),
        "temp_dir": str(temp_dir),
        "file_path": str(file_path) if file_path else None,
        "df": df,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "missing_values": int(df.isnull().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "created_at": now,
        "last_active": now,
        "summary": summary,
        "quality": quality,
        "report_path": None,
        "ai_requests": 0,
        "ask_requests": 0
    }

    with _LOCK:
        _SESSIONS[session_id] = session_data

    return session_data

def get_session(session_id):
    """
    Retrieve an active session by session_id.
    Returns None if session does not exist or has expired.
    Automatically refreshes last_active on valid access.
    """
    if not session_id:
        return None

    now = time.time()
    ttl = _get_ttl_seconds()

    with _LOCK:
        sess = _SESSIONS.get(session_id)
        if not sess:
            return None

        # Check expiration
        if now - sess.get('last_active', sess.get('created_at', 0)) > ttl:
            # Expired session: mark for cleanup
            is_expired = True
        else:
            is_expired = False
            sess['last_active'] = now

    if is_expired:
        clear_session(session_id)
        return None

    return sess

def clear_session(session_id):
    """
    Completely and immediately delete all temporary files and in-memory data for a session.
    Leaves 0 permanent data behind.
    """
    with _LOCK:
        sess = _SESSIONS.pop(session_id, None)

    if sess:
        temp_dir = sess.get('temp_dir')
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
        return True
    return False

def store_session_report(session_id, report_path):
    """Store generated report path on the session."""
    with _LOCK:
        sess = _SESSIONS.get(session_id)
        if sess:
            sess['report_path'] = str(report_path)
            sess['last_active'] = time.time()
            return True
    return False

def check_and_increment_limit(session_id, limit_type='ai'):
    """
    Check and increment abuse prevention quotas per temporary session.
    limit_type: 'ai' or 'ask'
    Returns True if allowed, False if limit reached.
    """
    with _LOCK:
        sess = _SESSIONS.get(session_id)
        if not sess:
            return False

        if limit_type == 'ai':
            if sess['ai_requests'] >= Config.MAX_AI_REQUESTS:
                return False
            sess['ai_requests'] += 1
            sess['last_active'] = time.time()
            return True
        elif limit_type == 'ask':
            if sess['ask_requests'] >= Config.MAX_ASK_REQUESTS:
                return False
            sess['ask_requests'] += 1
            sess['last_active'] = time.time()
            return True

    return False

def get_active_session_count():
    """Diagnostic helper for tests to inspect active in-memory sessions."""
    cleanup_expired_sessions()
    with _LOCK:
        return len(_SESSIONS)
