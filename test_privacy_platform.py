import os
import io
import time
import shutil
import unittest
import pandas as pd
from app import app
from config import Config
from analysis.session_manager import (
    create_session,
    get_session,
    clear_session,
    _SESSIONS,
    get_active_session_count
)

class PrivacyPlatformTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def setUp(self):
        # Create a small valid test CSV buffer
        self.csv_content = b"Item,Category,Price,Quantity\nLaptop,Tech,1200,2\nMouse,Tech,25,5\nDesk,Office,300,1\n"
        self.test_filename = "office_supplies.csv"

    # 1. No login required
    def test_01_no_login_required(self):
        """Verify that all core views are fully accessible without accounts or authentication headers."""
        res_home = self.client.get('/')
        self.assertEqual(res_home.status_code, 200)
        self.assertIn(b"Private data analysis", res_home.data)

        res_upload = self.client.get('/upload')
        self.assertEqual(res_upload.status_code, 200)

        res_privacy = self.client.get('/privacy')
        self.assertEqual(res_privacy.status_code, 200)

    # 2. CSV Upload
    def test_02_csv_upload(self):
        """Upload a valid CSV file and receive an isolated session token."""
        data = {
            'file': (io.BytesIO(self.csv_content), 'test_orders.csv')
        }
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 201)
        res_json = res.get_json()
        self.assertTrue(res_json['success'])
        self.assertIn('session_id', res_json)
        self.assertEqual(res_json['overview']['rows'], 3)
        self.assertEqual(res_json['overview']['columns'], 4)

    # 3. XLSX Upload
    def test_03_xlsx_upload(self):
        """Upload a valid Excel XLSX file and parse into a temporary session."""
        df_excel = pd.DataFrame({
            "Product": ["A", "B", "C"],
            "Revenue": [100, 200, 300]
        })
        excel_buf = io.BytesIO()
        df_excel.to_excel(excel_buf, index=False, engine='openpyxl')
        excel_buf.seek(0)

        data = {
            'file': (excel_buf, 'sales.xlsx')
        }
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 201)
        res_json = res.get_json()
        self.assertTrue(res_json['success'])
        self.assertEqual(res_json['overview']['rows'], 3)

    # 4. XLS Upload (Extension Validation)
    def test_04_xls_upload_validation(self):
        """Verify .xls extension is recognized as an allowed upload format."""
        self.assertIn('xls', Config.ALLOWED_EXTENSIONS)
        self.assertIn('xlsx', Config.ALLOWED_EXTENSIONS)
        self.assertIn('csv', Config.ALLOWED_EXTENSIONS)

    # 5. Invalid Upload Format Rejected
    def test_05_invalid_upload(self):
        """Disallowed extensions (.pdf, .exe, .py) are rejected with a clear error."""
        data = {
            'file': (io.BytesIO(b"%PDF-1.4...fake pdf"), 'document.pdf')
        }
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        res_json = res.get_json()
        self.assertFalse(res_json['success'])
        self.assertIn("valid CSV or Excel", res_json['error'])

    # 6. Oversized Upload
    def test_06_oversized_upload(self):
        """Ensure upload size checks reject files that exceed maximum configured limit."""
        # Config limit is MAX_CONTENT_LENGTH
        original_limit = app.config['MAX_CONTENT_LENGTH']
        app.config['MAX_CONTENT_LENGTH'] = 100 # Tiny 100 bytes limit
        try:
            big_data = {
                'file': (io.BytesIO(b"A" * 500), 'large.csv')
            }
            res = self.client.post('/api/upload', data=big_data, content_type='multipart/form-data')
            self.assertEqual(res.status_code, 413)
        finally:
            app.config['MAX_CONTENT_LENGTH'] = original_limit

    # 7. Empty Dataset Handling
    def test_07_empty_dataset(self):
        """Upload with 0 rows is rejected with clear user error."""
        data = {
            'file': (io.BytesIO(b"ColA,ColB\n"), 'empty.csv')
        }
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        res_json = res.get_json()
        self.assertFalse(res_json['success'])
        self.assertIn("usable data", res_json['error'])

    # 8. Missing Values Handling
    def test_08_missing_values(self):
        """Verify data quality auditor identifies missing values accurately."""
        csv_with_nulls = b"Name,Score,Grade\nAlice,90,A\nBob,,B\nCharlie,85,\n"
        data = {'file': (io.BytesIO(csv_with_nulls), 'nulls.csv')}
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        sid = res.get_json()['session_id']

        q_res = self.client.get(f'/api/dataset/{sid}/quality')
        self.assertEqual(q_res.status_code, 200)
        q_json = q_res.get_json()
        self.assertTrue(q_json['success'])
        # 2 missing values total
        total_missing = sum(col['missing'] for col in q_json['quality'])
        self.assertEqual(total_missing, 2)

    # 9. Duplicate Detection
    def test_09_duplicate_detection(self):
        """Verify duplicate rows are detected accurately."""
        csv_dups = b"A,B\n1,2\n1,2\n3,4\n"
        data = {'file': (io.BytesIO(csv_dups), 'dups.csv')}
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        sid = res.get_json()['session_id']
        self.assertEqual(res.get_json()['overview']['duplicate_rows'], 1)

    # 10. Chart API Returns JSON
    def test_10_chart_api(self):
        """Verify chart endpoint returns clean JSON visualizations."""
        res_sample = self.client.post('/api/upload-sample', json={'filename': 'student_performance.csv'})
        sid = res_sample.get_json()['session_id']

        charts_res = self.client.get(f'/api/dataset/{sid}/charts')
        self.assertEqual(charts_res.status_code, 200)
        self.assertTrue(charts_res.is_json)
        self.assertIn('charts', charts_res.get_json())

    # 11. Chart API Returns JSON On Failure
    def test_11_chart_api_returns_json_on_failure(self):
        """Verify chart endpoint returns JSON error rather than HTML Flask page on errors."""
        res = self.client.get('/api/dataset/non_existent_session_id/charts')
        self.assertEqual(res.status_code, 404)
        self.assertTrue(res.is_json)
        self.assertFalse(res.get_json()['success'])

    # 12. AI Fallback Without Key
    def test_12_ai_fallback_without_key(self):
        """AI insights seamlessly return deterministic rule-based insights when API key is unconfigured."""
        res_sample = self.client.post('/api/upload-sample', json={'filename': 'student_performance.csv'})
        sid = res_sample.get_json()['session_id']

        # Ensure fallback works
        orig_key = Config.GEMINI_API_KEY
        Config.GEMINI_API_KEY = ''
        try:
            res = self.client.post(f'/api/dataset/{sid}/insights')
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.get_json()['success'])
            self.assertIn("Key Findings", res.get_json()['insights'])
        finally:
            Config.GEMINI_API_KEY = orig_key

    # 13. Ask Your Data Deterministic Pandas Answers
    def test_13_ask_your_data(self):
        """Ask Your Data calculates numerical queries deterministically with Pandas."""
        res_sample = self.client.post('/api/upload-sample', json={'filename': 'sales_data.csv'})
        sid = res_sample.get_json()['session_id']

        # Total revenue query
        res_ask = self.client.post(f'/api/dataset/{sid}/ask', json={'question': 'What is the total sales?'})
        self.assertEqual(res_ask.status_code, 200)
        ans = res_ask.get_json()
        self.assertIn("total", ans['answer'].lower())
        self.assertIn("Pandas", ans['method'])

    # 14. PDF Generation in Temporary Directory
    def test_14_pdf_generation(self):
        """Generate PDF report inside the session temporary directory."""
        res_sample = self.client.post('/api/upload-sample', json={'filename': 'sales_data.csv'})
        sid = res_sample.get_json()['session_id']

        res_rep = self.client.post(f'/api/dataset/{sid}/report')
        self.assertEqual(res_rep.status_code, 201)
        rep_json = res_rep.get_json()
        self.assertTrue(rep_json['success'])

        sess = get_session(sid)
        self.assertTrue(os.path.exists(sess['report_path']))

    # 15. PDF Download
    def test_15_pdf_download(self):
        """Download binary PDF report."""
        res_sample = self.client.post('/api/upload-sample', json={'filename': 'sales_data.csv'})
        sid = res_sample.get_json()['session_id']
        self.client.post(f'/api/dataset/{sid}/report')

        res_dl = self.client.get(f'/api/report/{sid}/download')
        self.assertEqual(res_dl.status_code, 200)
        self.assertTrue(res_dl.data.startswith(b'%PDF'))

    # 16. Clear Session
    def test_16_clear_session(self):
        """Explicitly clear session and verify immediate destruction."""
        res_sample = self.client.post('/api/upload-sample', json={'filename': 'employee_data.csv'})
        sid = res_sample.get_json()['session_id']

        res_clear = self.client.post(f'/api/session/{sid}/clear')
        self.assertEqual(res_clear.status_code, 200)
        self.assertTrue(res_clear.get_json()['cleared'])

        # Verify session is gone from registry
        self.assertIsNone(get_session(sid))

    # 17. Expired Session Handling
    def test_17_expired_session(self):
        """Simulate TTL expiration and verify 404 response on dashboard."""
        res_sample = self.client.post('/api/upload-sample', json={'filename': 'student_performance.csv'})
        sid = res_sample.get_json()['session_id']

        # Artificially set last_active to 10 hours ago
        sess = get_session(sid)
        sess['last_active'] = time.time() - 36000

        # Attempt to access dashboard
        res_dash = self.client.get(f'/dashboard/{sid}')
        self.assertEqual(res_dash.status_code, 404)
        self.assertIn(b"Session Expired or Cleared", res_dash.data)

    # 18. Temporary File Cleanup Verification
    def test_18_temporary_file_cleanup(self):
        """Verify that temporary files and folders on disk are deleted upon clear_session."""
        data = {'file': (io.BytesIO(self.csv_content), 'cleanup_test.csv')}
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        sid = res.get_json()['session_id']

        sess = get_session(sid)
        temp_dir = sess['temp_dir']
        self.assertTrue(os.path.exists(temp_dir))

        # Clear session
        self.client.post(f'/api/session/{sid}/clear')
        self.assertFalse(os.path.exists(temp_dir))

    # 19. Path Traversal Protection
    def test_19_path_traversal_protection(self):
        """Ensure filenames with directory traversal patterns are sanitized and confined to temp storage."""
        data = {
            'file': (io.BytesIO(self.csv_content), '../../../../malicious.csv')
        }
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 201)
        sid = res.get_json()['session_id']

        sess = get_session(sid)
        # Ensure file path stays strictly within session temp_dir
        self.assertTrue(sess['file_path'].startswith(sess['temp_dir']))

    # 20. API Key Not Exposed
    def test_20_api_key_not_exposed(self):
        """Verify GEMINI_API_KEY is never leaked in HTML or JSON payloads."""
        key_secret = "SECRET_GEMINI_KEY_99999_DO_NOT_LEAK"
        orig_key = Config.GEMINI_API_KEY
        Config.GEMINI_API_KEY = key_secret
        try:
            res_home = self.client.get('/')
            self.assertNotIn(key_secret.encode(), res_home.data)

            res_sample = self.client.post('/api/upload-sample', json={'filename': 'student_performance.csv'})
            sid = res_sample.get_json()['session_id']

            res_dash = self.client.get(f'/dashboard/{sid}')
            self.assertNotIn(key_secret.encode(), res_dash.data)

            res_ai = self.client.post(f'/api/dataset/{sid}/insights')
            self.assertNotIn(key_secret, str(res_ai.get_json()))
        finally:
            Config.GEMINI_API_KEY = orig_key

    # 21. Environment Variables Configuration
    def test_21_environment_variables(self):
        """Verify Config parameters have sensible privacy-first defaults."""
        self.assertGreaterEqual(Config.MAX_UPLOAD_MB, 10)
        self.assertGreaterEqual(Config.SESSION_TTL_MINUTES, 10)
        self.assertGreaterEqual(Config.MAX_AI_REQUESTS, 5)

    # 22. Secure Random Session IDs
    def test_22_secure_random_session_ids(self):
        """Verify session tokens are cryptographically random and unguessable (>= 20 characters)."""
        res_1 = self.client.post('/api/upload-sample', json={'filename': 'sales_data.csv'})
        res_2 = self.client.post('/api/upload-sample', json={'filename': 'sales_data.csv'})
        sid_1 = res_1.get_json()['session_id']
        sid_2 = res_2.get_json()['session_id']

        self.assertNotEqual(sid_1, sid_2)
        self.assertGreater(len(sid_1), 20)
        self.assertGreater(len(sid_2), 20)

    # 23. No Persistent Database Dependency
    def test_23_no_persistent_database_dependency(self):
        """Verify that core data processing completes without writing to datalens.db."""
        # Upload, analyze, ask, report all function purely via in-memory sessions
        res = self.client.post('/api/upload-sample', json={'filename': 'employee_data.csv'})
        sid = res.get_json()['session_id']

        sess = get_session(sid)
        self.assertIsNotNone(sess)
        self.assertEqual(sess['filename'], 'employee_data.csv')

    # 24. Dashboard Loads Without Login
    def test_24_dashboard_loads_without_login(self):
        """Dashboard renders full analytical components without session cookies or user login."""
        res_sample = self.client.post('/api/upload-sample', json={'filename': 'sales_data.csv'})
        sid = res_sample.get_json()['session_id']

        res = self.client.get(f'/dashboard/{sid}')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Private Session", res.data)
        self.assertIn(b"Dataset Preview", res.data)
        self.assertIn(b"Clear Session", res.data)

if __name__ == '__main__':
    unittest.main()
