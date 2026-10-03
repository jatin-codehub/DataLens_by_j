# DataLens 🔍
### Privacy-First, No-Login, Temporary Data Analysis Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-black.svg)](https://flask.palletsprojects.com/)
[![Pandas](https://img.shields.io/badge/Pandas-2.0%2B-150458.svg)](https://pandas.pydata.org/)
[![Plotly](https://img.shields.io/badge/Plotly-5.0%2B-3F4F75.svg)](https://plotly.com/)
[![ReportLab](https://img.shields.io/badge/ReportLab-4.0%2B-green.svg)](https://www.reportlab.com/)
[![Google Gemini](https://img.shields.io/badge/Google-Gemini_AI-orange.svg)](https://aistudio.google.com/)
[![Vercel Ready](https://img.shields.io/badge/Vercel-Serverless_Ready-black.svg)](https://vercel.com/)

> **"DataLens — Private data analysis. No account required."**  
> **USP:** *No Login. No Data Library. Just Analyze.*

**DataLens** is an ephemeral, privacy-first data analytics platform. It allows users to upload CSV or Excel files, instantly compute descriptive statistics, audit data hygiene, visualize patterns with interactive Plotly graphs, synthesize structured AI insights with Google Gemini, query their data in plain English, and download executive PDF reports—**without requiring accounts, logins, or persistent data storage**.

---

## 🛡️ Privacy & Ephemeral Architecture

1. **No Account Required & Zero Profiling:** No email, password, OAuth, or user tracking.
2. **Cryptographically Isolated Sessions:** Every upload generates an unguessable 24-byte URL-safe token. Each session is completely isolated in its own filesystem sandbox (`/tmp/datalens_sessions/<session_id>/`).
3. **Automatic 30-Minute Purge:** Sessions automatically expire and are purged from disk after 30 minutes of inactivity.
4. **Instant "Clear Session" Destruction:** Users can click **Clear Session** at any time to instantly delete all uploaded files, cached data, and generated reports (`shutil.rmtree`).
5. **Privacy-Preserving AI:** Only minimized aggregate numbers (column names, counts, means, min/max) are ever sent to Gemini. **Raw rows and user files are never transmitted to external AI APIs.**
6. **Serverless & Read-Only Resilient:** Designed for deployment on Vercel and AWS Lambda where application roots are read-only. All runtime artifacts live in ephemeral `/tmp` storage.

---

## 🌟 Key Features

1. **Effortless Dataset Ingestion**
   - Drag-and-drop or file-picker upload for `.csv`, `.xlsx`, and `.xls` files (up to **25 MB**).
   - Robust encoding detection with fallbacks (`utf-8`, `latin1`, `cp1252`, `iso-8859-1`).
   - Duplicate column deduplication and identifier recognition.
   - Built-in 1-click sample datasets (`student_performance.csv`, `sales_data.csv`, `employee_data.csv`).

2. **Automated Statistical Analysis & Smart Typing**
   - Classifies columns into 6 distinct categories: `numeric`, `categorical`, `datetime`, `identifier`, `text`, and `boolean`.
   - Computes **Count**, **Mean**, **Median**, **Minimum**, **Maximum**, and **Standard Deviation** using Pandas.
   - Interactive preview of the first 15 records with column type badges.

3. **Data Quality & Hygiene Audit**
   - Detects null/missing cells and computes exact missing percentages per column.
   - Quality badges: **Good** (0%), **Warning** (<10%), or **Needs Attention** (≥10%).
   - Identifies duplicate rows and completely empty columns.

4. **Interactive Visualizations (Plotly)**
   - Smart chart selection:
     - Numerical distribution histograms with box margins.
     - Categorical frequency donut charts & bar charts.
     - Bivariate scatter plots with trendlines.
     - Multi-variable correlation heatmaps.
   - Fully interactive (zoom, pan, hover tooltips, and SVG/PNG export).

5. **AI Insights (Google Gemini 1.5 Flash)**
   - Structured findings: **Key Findings**, **Interesting Patterns**, **Data Quality Observations**, **Conclusions**, and **Limitations**.
   - **Graceful Offline Fallback:** If the Gemini API key is absent or quota is exceeded, DataLens automatically generates deterministic mathematical insights.

6. **"Ask Your Data" Safe Natural Language Q&A**
   - Answers questions like *"What is the average Math score?"*, *"What is the total revenue?"*, or *"Which department has the highest count?"*.
   - Evaluates calculations deterministically using Pandas first.
   - Never executes arbitrary untrusted AI-generated code or raw SQL queries.

7. **Visual Executive PDF Reports (ReportLab)**
   - 1-click downloadable publication-ready PDF reports with overview metrics, clean tables, embedded visual charts, and actionable findings.

---

## 🏗️ Project Architecture & Structure

```
DataLens/
│
├── app.py                     # Main Flask application & routes (Session-based, stateless)
├── config.py                  # App configuration, upload limits, TTL, and /tmp paths
├── requirements.txt           # Required Python packages
├── vercel.json                # Vercel serverless deployment routing config
├── .vercelignore              # Ignore rules for fast serverless builds
├── .env.example               # Template for environment variables
├── README.md                  # Comprehensive documentation & guide
│
├── api/
│   └── index.py               # WSGI wrapper normalizing PATH_INFO for Vercel serverless
│
├── analysis/
│   ├── __init__.py
│   ├── session_manager.py     # Ephemeral session manager with auto-purge & quota tracking
│   ├── analyzer.py            # Statistical summaries & 6-type column categorization
│   ├── cleaner.py             # Data quality audit (missing values, duplicates, datatypes)
│   └── visualizer.py          # Interactive Plotly chart generators
│
├── ai/
│   ├── __init__.py
│   └── insights.py            # Structured Gemini API integration & safe Q&A engine
│
├── reports/
│   ├── __init__.py
│   └── pdf_generator.py       # Professional ReportLab visual PDF generator
│
├── templates/
│   ├── index.html             # Privacy-focused landing page with 5-step process & trust section
│   ├── upload.html            # Drag-and-drop file upload with 25MB validation
│   ├── dashboard.html         # 11-step analytics dashboard with Privacy Banner & Clear Session modal
│   ├── report.html            # Report download & overview page
│   ├── privacy.html           # Dedicated Privacy Policy page
│   └── error.html             # Friendly error display
│
├── static/
│   ├── css/
│   │   └── style.css          # Restrained, modern data analytics UI styling
│   └── js/
│       ├── upload.js          # File upload handler with 25MB check
│       └── dashboard.js       # Dynamic charts, statistics table, AI insights, Q&A, and Clear Session
│
├── sample_data/               # Built-in sample datasets (Student, Sales, Employee)
├── test_privacy_platform.py   # Comprehensive test suite (24 privacy/session tests)
├── test_datalens.py           # Core platform test suite (15 tests)
└── test_pdf_redesign.py       # PDF engine test suite (10 tests)
```

---

## ⚙️ Installation & Local Setup

### Prerequisites
- Python 3.10+ installed.

### Step 1: Clone or Navigate to the Directory
```bash
git clone https://github.com/jatin-codehub/DataLens_by_j.git
cd DataLens_by_j
```

### Step 2: (Optional) Create a Python Virtual Environment
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Optionally paste your Google Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
MAX_UPLOAD_MB=25
SESSION_TTL_MINUTES=30
```
> *Note: If no Gemini API key is configured, DataLens will run completely using its built-in deterministic mathematical analysis engine.*

### Step 5: Start the Application
```bash
python app.py
```
Open your browser at:
```
http://127.0.0.1:5000
```

---

## ☁️ Deploying to Vercel

DataLens is pre-configured for 1-click deployment on **Vercel**:

1. Push your repository to GitHub.
2. In your Vercel Dashboard, click **Add New Project** and select your repository.
3. Configure the Environment Variables in Vercel:
   - `GEMINI_API_KEY`: Your Gemini API key (optional).
   - `SECRET_KEY`: A random secret string.
   - `MAX_UPLOAD_MB`: `25`
   - `SESSION_TTL_MINUTES`: `30`
4. Click **Deploy**.
5. Vercel automatically routes requests through `vercel.json` and `api/index.py`.

---

## 🧪 Automated Testing

DataLens includes 3 test suites covering 49 total automated tests:

```bash
# 1. Test Privacy Platform Architecture & Sessions (24 tests)
python test_privacy_platform.py

# 2. Test Core Uploads, Data Quality & Analysis (15 tests)
python test_datalens.py

# 3. Test Visual PDF Report Generation (10 tests)
python test_pdf_redesign.py
```

---

## 📜 Privacy Statement
DataLens is committed to user privacy. We do not require accounts, we do not build user profiles, we do not store datasets in a permanent database, and we do not retain files after sessions expire or are cleared. For details, visit `/privacy`.

## 📄 License
Open source for educational and academic presentation purposes.
