# DataLens 🔍
### AI-Powered Data Analysis & Reporting Dashboard

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-black.svg)](https://flask.palletsprojects.com/)
[![Pandas](https://img.shields.io/badge/Pandas-2.0%2B-150458.svg)](https://pandas.pydata.org/)
[![Plotly](https://img.shields.io/badge/Plotly-5.0%2B-3F4F75.svg)](https://plotly.com/)
[![ReportLab](https://img.shields.io/badge/ReportLab-4.0%2B-green.svg)](https://www.reportlab.com/)
[![Google Gemini](https://img.shields.io/badge/Google-Gemini_AI-orange.svg)](https://aistudio.google.com/)

**DataLens** is a full-stack data analytics and automated reporting web application designed as a 2nd-year CSE / Data Science mini-project. It enables users to upload CSV or Excel datasets, instantly compute statistical summaries, audit data quality, visualize patterns interactively using Plotly, synthesize structured AI insights with Google Gemini, query their data in plain English, and download executive PDF reports generated with ReportLab.

---

## 🌟 Key Features

1. **Effortless Dataset Ingestion**
   - Drag-and-drop or file-picker upload for `.csv`, `.xlsx`, and `.xls` files (up to 10 MB).
   - Validates file extensions, file integrity, and non-empty content with user-friendly alerts.
   - Built-in 1-click sample datasets (`student_performance.csv`, `sales_data.csv`, `employee_data.csv`) for fast college presentations.

2. **Automated Statistical Analysis**
   - Automatic classification into **Numerical**, **Categorical**, and **Datetime** dimensions.
   - Computes **Count**, **Mean**, **Median**, **Minimum**, **Maximum**, and **Standard Deviation** with Pandas.
   - Interactive preview of the first 15 records with column data types.

3. **Data Quality & Hygiene Audit**
   - Detects null/missing cells and computes exact missing percentages per column.
   - Health badges: <span style="color:green">**Good**</span> (0%), <span style="color:orange">**Warning**</span> (<10%), or <span style="color:red">**Needs Attention**</span> (≥10%).
   - Identifies duplicate rows and completely empty columns without altering the user's raw dataset silently.

4. **Interactive Visualizations (Plotly)**
   - Smart chart selection:
     - Numerical distribution histograms with box margins.
     - Categorical frequency donut charts & bar charts.
     - Bivariate scatter plots with trendlines.
     - Multi-variable correlation heatmaps.
   - Fully interactive (zoom, pan, hover tooltips, and image export).

5. **AI Insights (Google Gemini 1.5 Flash)**
   - **Privacy-first token economy:** Never sends massive raw data tables to the cloud; sends only structured statistical summaries.
   - Generates educational findings: **Key Findings**, **Interesting Patterns**, **Data Quality Observations**, **Possible Conclusions**, and **Limitations** (e.g., correlation does not equal causation).
   - **Graceful Offline Fallback:** If the Gemini API key is absent or offline, DataLens automatically provides clean, rule-based mathematical insights.

6. **"Ask Your Data" Safe Natural Language Q&A**
   - Answers questions like *"What is the average Math score?"*, *"How many rows are there?"*, or *"Which department has the highest average?"*.
   - Evaluates calculations deterministically using Pandas first.
   - Never executes arbitrary untrusted AI-generated code or unsanitized SQL.

7. **Executive PDF Reports (ReportLab)**
   - 1-click downloadable publication-ready PDF reports formatted with tables, overview metrics, data quality scores, and analytical conclusions.

---

## 🏗️ Project Architecture & Structure

```
DataLens/
│
├── app.py                     # Main Flask application & routes (Pages + REST API)
├── config.py                  # App configuration, upload limits, secret keys
├── requirements.txt           # Required Python packages
├── .env.example               # Template for environment variables (GEMINI_API_KEY)
├── .gitignore                 # Git ignore rules for virtualenvs, uploads, db
├── README.md                  # Comprehensive documentation & viva guide
├── test_datalens.py           # Automated test suite (15 unit/integration tests)
│
├── database/
│   ├── __init__.py
│   ├── database.py            # SQLite helper functions with safe connection management
│   └── schema.sql             # SQL schema for datasets, analyses, and reports
│
├── analysis/
│   ├── __init__.py
│   ├── analyzer.py            # Statistical summaries (mean, median, min, max, std, types)
│   ├── cleaner.py             # Data quality audit (missing values, duplicates, datatypes)
│   └── visualizer.py          # Interactive Plotly chart generators
│
├── ai/
│   ├── __init__.py
│   └── insights.py            # Structured Gemini API integration & safe Q&A engine
│
├── reports/
│   ├── __init__.py
│   └── pdf_generator.py       # Professional ReportLab PDF generation
│
├── templates/
│   ├── index.html             # Professional landing page
│   ├── upload.html            # Drag-and-drop file upload with validation & loading states
│   ├── dashboard.html         # Analytics dashboard (summary cards, preview, charts, AI, Q&A)
│   ├── report.html            # Report download & overview page
│   └── error.html             # Friendly error display
│
├── static/
│   ├── css/
│   │   └── style.css          # Clean, modern analytics UI styling
│   └── js/
│       ├── upload.js          # File drag-and-drop, validation, and upload handler
│       └── dashboard.js       # Dynamic chart rendering, AI insights, and Q&A interactions
│
├── uploads/                   # Stored uploaded CSV/XLSX files
├── generated_reports/         # Saved PDF reports
└── sample_data/
    ├── student_performance.csv # Realistic 72-row student dataset for college demo
    ├── sales_data.csv          # Realistic retail sales transactions
    └── employee_data.csv       # HR/employee dataset
```

---

## ⚙️ Installation & Windows Setup

### Prerequisites
- Python 3.10+ installed on your computer.
- Git (optional).

### Step 1: Open PowerShell or Command Prompt
Navigate to the project directory:
```powershell
cd C:\Users\<YourUsername>\Desktop\Datalens
```

### Step 2: (Optional) Create a Python Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Open `.env` in any text editor (like Notepad or VS Code) and optionally paste your Google Gemini API key:
```env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=datalens_secure_college_project_key_2026
GEMINI_API_KEY=your_gemini_api_key_here
```
> **Note:** If you do not have a Gemini API key yet, DataLens will still run completely and will automatically use its built-in deterministic rule-based analysis engine!

---

## 🚀 Running the Application

Start the Flask server:
```powershell
python app.py
```

Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🧪 Running Automated Tests

DataLens includes an automated test suite verifying all 15 core scenarios (CSV uploads, Excel uploads, invalid formats, missing values, duplicates, numeric/categorical charts, AI insights, Q&A, and PDF generation):

```powershell
python test_datalens.py
```
Output:
```
Ran 15 tests in 1.375s
OK
```

---

## 🎓 College Viva & Presentation Guide

As a 2nd-year CSE/Data Science student, you can easily explain how each component of DataLens functions:

### 1. What does Flask do?
*Flask is a lightweight Python WSGI web framework. It handles incoming HTTP requests from the browser, routes them to specific functions (`/upload`, `/dashboard/<id>`, `/api/...`), executes business logic, queries SQLite, and either renders Jinja2 HTML templates or returns JSON for asynchronous JavaScript fetch calls.*

### 2. What does Pandas do?
*Pandas is the data manipulation backbone. It reads CSV or Excel files into two-dimensional data structures called DataFrames. It allows us to calculate descriptive statistics (`mean()`, `median()`, `min()`, `max()`, `std()`), inspect null values (`isnull().sum()`), and detect duplicated rows (`duplicated().sum()`) in milliseconds.*

### 3. How are missing values detected?
*`df.isnull().sum()` computes the count of null/NaN cells for every column. By dividing this count by `len(df)` and multiplying by 100, we obtain the missing percentage. Columns are then categorized into 'Good' (0%), 'Warning' (<10%), or 'Needs Attention' (≥10%).*

### 4. How does Plotly create charts?
*Python uses `plotly.express` to generate data visualizations based on column datatypes. Instead of rendering static PNG images on the server, Python exports the chart structure into JSON (`fig.to_json()`). The browser receives this JSON and uses client-side `Plotly.js` to render interactive SVG/WebGL charts that users can hover, zoom, and explore.*

### 5. Why do we NOT send the whole dataset to the AI?
*Sending thousands of raw data rows to an LLM wastes API tokens, exceeds context limits, risks leaking sensitive personal data, and increases latency. Instead, we use Pandas to summarize the dataset into a compact statistical JSON schema (~150 tokens) and send only that summary to Google Gemini.*

### 6. How does "Ask Your Data" prevent security risks?
*We do not let the AI generate executable Python code or SQL directly on the server (which could lead to remote code execution or SQL injection). Instead, user questions are parsed and evaluated deterministically using predefined Pandas functions.*

### 7. How does SQLite store metadata?
*SQLite is a lightweight, serverless relational database stored in a single local file (`datalens.db`). It stores metadata such as dataset IDs, filenames, row/column counts, missing values, cached analysis summaries, and generated report records.*

### 8. How does ReportLab generate the PDF?
*ReportLab constructs a flowable document structure (`SimpleDocTemplate`). It organizes paragraphs, custom styles, horizontal dividers, and tables (`Table`, `TableStyle`) into a printable letter-sized PDF document and streams it directly to the user's browser.*

---

## ⏱️ 5-Minute College Demonstration Walkthrough

When presenting this project to an examiner or professor:

1. **Open DataLens:** Show the clean landing page (`http://127.0.0.1:5000`). Highlight the modern UI and responsive layout.
2. **1-Click Sample Dataset:** In the "Sample Data" section, click **"Analyze This Dataset"** on **Student Performance** (`student_performance.csv`).
3. **Show Overview Cards:** Point out the immediate metrics: 72 rows, 10 columns, 3 missing values, and 2 duplicate rows.
4. **Dataset Preview:** Scroll through the first 15 records showing column data types.
5. **Statistical Summary:** Highlight the automated mean, median, min, max, and standard deviation calculated for Math, Physics, Programming, Attendance, and Study Hours.
6. **Data Quality Audit:** Show how missing values are identified with status badges and explain the duplicate row detection notice.
7. **Interactive Charts:** Hover over the histograms and scatter plot (Math vs. Physics) to show interactive tooltips.
8. **AI Insights:** Showcase the 5-point report (Key Findings, Patterns, Quality, Conclusions, Limitations). Click **"Regenerate Insights"** to demonstrate responsiveness.
9. **Ask Your Data:** Type: *"What is the average Math score?"* or click one of the suggested chips. Show how the exact calculation is derived instantly.
10. **Generate & Download PDF:** Click **"Generate PDF Report"**, let the modal process, and click **"Download PDF"** to open the generated report.

---

## 🔮 Future Enhancements (Roadmap)

- **User Authentication:** Multi-user accounts with secure password hashing (Bcrypt).
- **Cloud Database:** Migration path from SQLite to PostgreSQL.
- **Machine Learning Integrations:** Automated linear regression or classification baseline models (Scikit-Learn).
- **Time-Series Forecasting:** Automated ARIMA or Prophet trend predictions.
- **Export Formats:** Excel and Word (.docx) export options alongside PDF.

---

## 📜 License
Developed as an educational mini-project for Computer Science & Data Science students. Open source for academic learning and presentation purposes.
