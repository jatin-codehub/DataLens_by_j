import sys
from pathlib import Path

# Add project root directory to sys.path so app and internal modules are discoverable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app as flask_app

def app(environ, start_response):
    """
    WSGI wrapper for Vercel deployment.
    When Vercel rewrites routes to /api/index, it sends the original requested path
    in HTTP_X_MATCHED_PATH (or x-matched-path). We restore PATH_INFO to match Flask routes.
    """
    matched_path = (
        environ.get('HTTP_X_MATCHED_PATH')
        or environ.get('x-matched-path')
        or environ.get('HTTP_X_FORWARDED_URI')
        or environ.get('X-Matched-Path')
        or environ.get('HTTP_HTTP_X_MATCHED_PATH')
    )
    if matched_path:
        # Strip query parameters if present
        environ['PATH_INFO'] = matched_path.split('?')[0]
    elif environ.get('PATH_INFO') in ('/api/index', '/api/index.py'):
        # Fallback if accessed directly at entrypoint
        environ['PATH_INFO'] = '/'

    return flask_app(environ, start_response)
