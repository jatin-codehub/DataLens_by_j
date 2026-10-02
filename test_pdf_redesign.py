import os
import io
import unittest
import pandas as pd
import numpy as np

from app import app
from database.database import init_db
from reports.pdf_generator import generate_pdf_report
from reports.chart_generator import select_useful_charts
from analysis.analyzer import get_dataset_overview, detect_column_types
from analysis.cleaner import check_data_quality

class TestPdfRedesign(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()
        init_db()
        os.makedirs('test_reports', exist_ok=True)

    def verify_pdf_generation(self, df, filename):
        """Helper to test PDF generation for any DataFrame."""
        meta = {
            'filename': filename,
            'file_type': 'csv',
            'rows': len(df),
            'columns': len(df.columns),
            'missing_values': int(df.isnull().sum().sum()),
            'duplicate_rows': int(df.duplicated().sum())
        }
        col_types = detect_column_types(df)
        summary = get_dataset_overview(df)
        quality = check_data_quality(df)
        ai_insights = "Key observations from dataset summary:\n- Sample distribution is balanced.\n- Key variables recorded accurately."

        out_path = os.path.join('test_reports', f"{filename.replace('.csv', '')}_report.pdf")
        if os.path.exists(out_path):
            os.remove(out_path)

        res_path = generate_pdf_report(meta, summary, quality, df, ai_insights, out_path)
        self.assertTrue(os.path.exists(res_path))
        file_size = os.path.getsize(res_path)
        self.assertGreater(file_size, 5000, f"PDF file size too small: {file_size}")
        
        # Verify chart selection logic
        charts = select_useful_charts(df, col_types)
        self.assertLessEqual(len(charts), 4, "Charts count exceeds 4 limit")
        return res_path, len(charts), file_size

    def test_01_student_dataset(self):
        """1. Student dataset testing."""
        df = pd.read_csv('sample_data/student_performance.csv')
        path, n_charts, size = self.verify_pdf_generation(df, 'student_test.csv')
        self.assertGreater(n_charts, 0)
        print(f"[PASS] Student dataset: {n_charts} charts generated, PDF size: {size:,} bytes")

    def test_02_sales_dataset(self):
        """2. Ecommerce/Sales dataset testing."""
        df = pd.read_csv('sample_data/sales_data.csv')
        path, n_charts, size = self.verify_pdf_generation(df, 'sales_test.csv')
        self.assertGreater(n_charts, 0)
        print(f"[PASS] Sales dataset: {n_charts} charts generated, PDF size: {size:,} bytes")

    def test_03_employee_dataset(self):
        """3. Employee dataset testing."""
        df = pd.read_csv('sample_data/employee_data.csv')
        path, n_charts, size = self.verify_pdf_generation(df, 'employee_test.csv')
        self.assertGreater(n_charts, 0)
        print(f"[PASS] Employee dataset: {n_charts} charts generated, PDF size: {size:,} bytes")

    def test_04_numerical_only(self):
        """4. Numerical-only dataset."""
        df = pd.DataFrame({
            'Feature_A': np.random.normal(50, 10, 100),
            'Feature_B': np.random.uniform(10, 80, 100),
            'Feature_C': np.random.exponential(5, 100)
        })
        path, n_charts, size = self.verify_pdf_generation(df, 'numerical_only.csv')
        self.assertGreater(n_charts, 0)
        print(f"[PASS] Numerical-only dataset: {n_charts} charts generated, PDF size: {size:,} bytes")

    def test_05_categorical_only(self):
        """5. Categorical-only dataset."""
        df = pd.DataFrame({
            'City': ['Mumbai', 'Delhi', 'Bangalore', 'Chennai'] * 25,
            'Status': ['Active', 'Pending', 'Active', 'Inactive'] * 25,
            'Tier': ['Tier 1', 'Tier 2', 'Tier 1', 'Tier 3'] * 25
        })
        path, n_charts, size = self.verify_pdf_generation(df, 'categorical_only.csv')
        self.assertGreater(n_charts, 0)
        print(f"[PASS] Categorical-only dataset: {n_charts} charts generated, PDF size: {size:,} bytes")

    def test_06_mixed_dataset(self):
        """6. Mixed dataset."""
        df = pd.DataFrame({
            'Product': ['A', 'B', 'C', 'D'] * 20,
            'Rating': np.random.uniform(1, 5, 80),
            'Revenue': np.random.uniform(100, 1000, 80),
            'In_Stock': [True, False, True, True] * 20
        })
        path, n_charts, size = self.verify_pdf_generation(df, 'mixed_test.csv')
        self.assertGreater(n_charts, 0)
        print(f"[PASS] Mixed dataset: {n_charts} charts generated, PDF size: {size:,} bytes")

    def test_07_missing_values(self):
        """7. Dataset with missing values."""
        df = pd.read_csv('sample_data/student_performance.csv')
        # Inject more missing values
        df.loc[0:5, 'Attendance'] = np.nan
        df.loc[10:15, 'Math'] = np.nan
        path, n_charts, size = self.verify_pdf_generation(df, 'missing_vals_test.csv')
        print(f"[PASS] Missing values dataset: {n_charts} charts generated, PDF size: {size:,} bytes")

    def test_08_duplicate_rows(self):
        """8. Dataset with duplicate rows."""
        df = pd.read_csv('sample_data/sales_data.csv')
        # Duplicate top 10 rows
        df = pd.concat([df, df.head(10)], ignore_index=True)
        path, n_charts, size = self.verify_pdf_generation(df, 'duplicates_test.csv')
        print(f"[PASS] Duplicate rows dataset: {n_charts} charts generated, PDF size: {size:,} bytes")

    def test_09_date_column_time_series(self):
        """9. Dataset with a genuine date column."""
        dates = pd.date_range('2026-01-01', periods=30, freq='D')
        df = pd.DataFrame({
            'Date': dates.strftime('%Y-%m-%d'),
            'Daily_Visitors': np.random.randint(100, 500, 30),
            'Daily_Revenue': np.random.uniform(200, 1000, 30),
            'Category': (['Mobile', 'Desktop'] * 15)
        })
        path, n_charts, size = self.verify_pdf_generation(df, 'date_time_test.csv')
        self.assertGreater(n_charts, 0)
        print(f"[PASS] Date column dataset: {n_charts} charts generated, PDF size: {size:,} bytes")

    def test_10_api_endpoint_flow(self):
        """Verify full Flask upload -> report generation -> download flow."""
        res = self.client.post('/api/upload-sample', json={'filename': 'student_performance.csv'})
        self.assertEqual(res.status_code, 200)
        dataset_id = res.get_json()['dataset_id']

        # Generate report
        gen_res = self.client.post(f'/api/dataset/{dataset_id}/report')
        self.assertEqual(gen_res.status_code, 201)
        report_id = gen_res.get_json()['report_id']

        # Download report
        dl_res = self.client.get(f'/api/report/{report_id}/download')
        self.assertEqual(dl_res.status_code, 200)
        self.assertEqual(dl_res.content_type, 'application/pdf')
        self.assertGreater(len(dl_res.data), 10000)
        dl_res.close()
        print(f"[PASS] Full API endpoint generation and download verified ({len(dl_res.data):,} bytes)")

if __name__ == '__main__':
    unittest.main()
