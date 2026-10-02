import os
import sqlite3
import json
from pathlib import Path
from contextlib import contextmanager
from config import Config

SCHEMA_PATH = Path(__file__).resolve().parent / 'schema.sql'

@contextmanager
def get_db_connection():
    """Create a connection context that commits and automatically closes."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    """Create database tables based on schema.sql if they do not exist."""
    os.makedirs(os.path.dirname(str(Config.DATABASE_PATH)), exist_ok=True)
    with get_db_connection() as conn:
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())


def save_dataset_metadata(dataset_id, filename, file_type, rows, cols, missing, duplicates):
    """Save metadata of an uploaded dataset."""
    with get_db_connection() as conn:
        conn.execute('''
            INSERT INTO datasets (id, filename, file_type, rows, columns, missing_values, duplicate_rows)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (dataset_id, filename, file_type, rows, cols, missing, duplicates))

def get_dataset_metadata(dataset_id):
    """Retrieve metadata of a dataset by its unique ID."""
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM datasets WHERE id = ?', (dataset_id,)).fetchone()
        return dict(row) if row else None

def save_analysis_summary(dataset_id, summary_dict):
    """Cache the JSON analysis summary in the database."""
    with get_db_connection() as conn:
        conn.execute('''
            INSERT INTO analyses (dataset_id, summary)
            VALUES (?, ?)
        ''', (dataset_id, json.dumps(summary_dict)))

def get_latest_analysis(dataset_id):
    """Retrieve the latest cached analysis summary for a dataset."""
    with get_db_connection() as conn:
        row = conn.execute('''
            SELECT summary FROM analyses WHERE dataset_id = ? ORDER BY id DESC LIMIT 1
        ''', (dataset_id,)).fetchone()
        return json.loads(row['summary']) if row else None

def save_report_record(report_id, dataset_id, filename):
    """Save record of a generated PDF report."""
    with get_db_connection() as conn:
        conn.execute('''
            INSERT INTO reports (id, dataset_id, filename)
            VALUES (?, ?, ?)
        ''', (report_id, dataset_id, filename))

def get_report_record(report_id):
    """Fetch report information by report ID."""
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM reports WHERE id = ?', (report_id,)).fetchone()
        return dict(row) if row else None
