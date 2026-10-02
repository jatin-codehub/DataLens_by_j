import os
import io
import json
import unittest
import pandas as pd
import numpy as np

from app import app
from database.database import init_db

class DataLensTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Configure test client
        app.config['TESTING'] = True
        cls.client = app.test_client()
        init_db()

    def test_01_upload_valid_csv(self):
        """TEST 1: Upload valid CSV."""
        csv_content = b"Student_ID,Name,Age,Math,Physics\n1,Alex,20,85,90\n2,Beth,21,92,88\n"
        data = {
            'file': (io.BytesIO(csv_content), 'alex_test.csv')
        }
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 201)
        res_json = res.get_json()
        self.assertTrue(res_json['success'])
        self.assertIn('dataset_id', res_json)
        self.assertEqual(res_json['overview']['rows'], 2)
        self.assertEqual(res_json['overview']['columns'], 5)

    def test_02_upload_valid_excel(self):
        """TEST 2: Upload valid Excel."""
        df = pd.DataFrame({
            "Item": ["Pen", "Notebook", "Desk"],
            "Price": [1.5, 4.0, 120.0],
            "Stock": [50, 20, 5]
        })
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)

        data = {
            'file': (buffer, 'inventory.xlsx')
        }
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 201)
        res_json = res.get_json()
        self.assertTrue(res_json['success'])
        self.assertEqual(res_json['overview']['rows'], 3)

    def test_03_upload_invalid_file(self):
        """TEST 3: Upload invalid file format."""
        data = {
            'file': (io.BytesIO(b"Hello world"), 'document.pdf')
        }
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        res_json = res.get_json()
        self.assertFalse(res_json['success'])
        self.assertIn("valid CSV or Excel", res_json['error'])

    def test_04_dataset_with_missing_values(self):
        """TEST 4: Dataset with missing values."""
        csv_content = b"Col1,Col2\n10,\n,20\n30,40\n"
        data = {'file': (io.BytesIO(csv_content), 'missing_test.csv')}
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 201)
        dataset_id = res.get_json()['dataset_id']

        q_res = self.client.get(f'/api/dataset/{dataset_id}/quality')
        self.assertEqual(q_res.status_code, 200)
        q_json = q_res.get_json()
        self.assertTrue(q_json['success'])
        # Verify missing counts detected
        self.assertEqual(q_json['quality'][0]['missing'], 1)
        self.assertEqual(q_json['quality'][1]['missing'], 1)

    def test_05_dataset_with_duplicate_rows(self):
        """TEST 5: Dataset with duplicate rows."""
        csv_content = b"A,B\n1,X\n1,X\n2,Y\n"
        data = {'file': (io.BytesIO(csv_content), 'duplicate_test.csv')}
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 201)
        dataset_id = res.get_json()['dataset_id']

        q_res = self.client.get(f'/api/dataset/{dataset_id}/quality')
        q_json = q_res.get_json()
        self.assertEqual(q_json['cleaning']['duplicate_rows'], 1)
        self.assertEqual(q_json['cleaning']['clean_rows_estimate'], 2)

    def test_06_dataset_only_numerical_columns(self):
        """TEST 6: Dataset with only numerical columns."""
        csv_content = b"N1,N2,N3\n10,20,30\n40,50,60\n70,80,90\n"
        data = {'file': (io.BytesIO(csv_content), 'numeric_only.csv')}
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        dataset_id = res.get_json()['dataset_id']

        s_res = self.client.get(f'/api/dataset/{dataset_id}/statistics')
        s_json = s_res.get_json()
        self.assertEqual(len(s_json['statistics']), 3)
        self.assertEqual(s_json['statistics']['N1']['mean'], 40.0)

    def test_07_dataset_with_categorical_columns(self):
        """TEST 7: Dataset with categorical columns."""
        csv_content = b"Category,Grade\nElectronics,A\nClothing,B\nElectronics,A\n"
        data = {'file': (io.BytesIO(csv_content), 'categorical.csv')}
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        dataset_id = res.get_json()['dataset_id']

        c_res = self.client.get(f'/api/dataset/{dataset_id}/charts')
        c_json = c_res.get_json()
        self.assertTrue(c_json['success'])
        self.assertTrue(any(c['type'] == 'category' for c in c_json['charts']))

    def test_08_dataset_with_mixed_columns(self):
        """TEST 8: Dataset with mixed columns (Sample student performance)."""
        res = self.client.post('/api/upload-sample', json={'filename': 'student_performance.csv'})
        self.assertEqual(res.status_code, 200)
        dataset_id = res.get_json()['dataset_id']

        d_res = self.client.get(f'/api/dataset/{dataset_id}')
        self.assertEqual(d_res.status_code, 200)
        self.assertTrue(d_res.get_json()['success'])

    def test_09_generate_ai_insights(self):
        """TEST 9: Generate AI insights (Gemini or reliable rule-based fallback)."""
        res = self.client.post('/api/upload-sample', json={'filename': 'student_performance.csv'})
        dataset_id = res.get_json()['dataset_id']

        ai_res = self.client.post(f'/api/dataset/{dataset_id}/insights')
        self.assertEqual(ai_res.status_code, 200)
        ai_json = ai_res.get_json()
        self.assertTrue(ai_json['success'])
        self.assertIn("Key Findings", ai_json['insights'])
        self.assertIn("Limitations", ai_json['insights'])

    def test_10_ask_dataset_question(self):
        """TEST 10: Ask dataset questions."""
        res = self.client.post('/api/upload-sample', json={'filename': 'student_performance.csv'})
        dataset_id = res.get_json()['dataset_id']

        # Average question
        q1 = self.client.post(f'/api/dataset/{dataset_id}/ask', json={'question': 'What is the average Math score?'})
        self.assertEqual(q1.status_code, 200)
        ans1 = q1.get_json()
        self.assertIn("average (mean) of **Math**", ans1['answer'])

        # Total rows question
        q2 = self.client.post(f'/api/dataset/{dataset_id}/ask', json={'question': 'How many rows are there?'})
        self.assertEqual(q2.status_code, 200)
        ans2 = q2.get_json()
        self.assertIn("rows", ans2['answer'])

    def test_11_generate_pdf(self):
        """TEST 11: Generate PDF report."""
        res = self.client.post('/api/upload-sample', json={'filename': 'student_performance.csv'})
        dataset_id = res.get_json()['dataset_id']

        pdf_res = self.client.post(f'/api/dataset/{dataset_id}/report')
        self.assertEqual(pdf_res.status_code, 201)
        pdf_json = pdf_res.get_json()
        self.assertTrue(pdf_json['success'])
        self.assertIn('report_id', pdf_json)

    def test_12_download_pdf(self):
        """TEST 12: Download PDF report."""
        res = self.client.post('/api/upload-sample', json={'filename': 'student_performance.csv'})
        dataset_id = res.get_json()['dataset_id']

        pdf_res = self.client.post(f'/api/dataset/{dataset_id}/report')
        report_id = pdf_res.get_json()['report_id']

        dl_res = self.client.get(f'/api/report/{report_id}/download')
        self.assertEqual(dl_res.status_code, 200)
        self.assertEqual(dl_res.content_type, 'application/pdf')
        self.assertTrue(len(dl_res.data) > 1000)
        dl_res.close()

    def test_13_invalid_dataset_id(self):
        """TEST 13: Invalid dataset ID."""
        res = self.client.get('/api/dataset/non_existent_id_999')
        self.assertEqual(res.status_code, 404)

        page_res = self.client.get('/dashboard/non_existent_id_999')
        self.assertEqual(page_res.status_code, 404)
        self.assertIn(b"Dataset Not Found", page_res.data)

    def test_14_ai_api_unavailable_handling(self):
        """TEST 14: Graceful handling when Gemini API key is absent or invalid."""
        csv_content = b"Score\n75\n85\n95\n"
        data = {'file': (io.BytesIO(csv_content), 'ai_test.csv')}
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        dataset_id = res.get_json()['dataset_id']

        ai_res = self.client.post(f'/api/dataset/{dataset_id}/insights')
        self.assertEqual(ai_res.status_code, 200)
        ai_json = ai_res.get_json()
        # Should gracefully return insights via local fallback
        self.assertTrue(ai_json['success'])
        self.assertTrue(len(ai_json['insights']) > 0)

    def test_15_empty_dataset(self):
        """TEST 15: Empty dataset rejected properly."""
        csv_content = b"ColA,ColB\n"  # Headers only, no rows
        data = {'file': (io.BytesIO(csv_content), 'empty.csv')}
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        res_json = res.get_json()
        self.assertFalse(res_json['success'])
        self.assertIn("does not contain usable data", res_json['error'])

if __name__ == '__main__':
    unittest.main()
