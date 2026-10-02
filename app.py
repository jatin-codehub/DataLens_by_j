import os
import uuid
import shutil
from pathlib import Path
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file
from werkzeug.utils import secure_filename

from config import Config
from database.database import (
    init_db,
    save_dataset_metadata,
    get_dataset_metadata,
    save_analysis_summary,
    get_latest_analysis,
    save_report_record,
    get_report_record
)
from analysis.analyzer import (
    load_dataset,
    detect_column_types,
    calculate_numerical_statistics,
    get_preview,
    get_dataset_overview
)
from analysis.cleaner import check_data_quality, get_cleaning_summary
from analysis.visualizer import generate_visualizations
from ai.insights import generate_ai_insights, answer_dataset_question
from reports.pdf_generator import generate_pdf_report

BASE_DIR = Path(__file__).resolve().parent

# Initialize Flask application with explicit absolute paths
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / 'templates'),
    static_folder=str(BASE_DIR / 'static')
)
app.config.from_object(Config)

# Ensure runtime directories exist (routed to /tmp on serverless like Vercel)
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.REPORTS_FOLDER, exist_ok=True)

# Initialize SQLite database schema
init_db()

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def get_dataset_file_path(dataset_id, file_type):
    """Resolve file path for a stored dataset."""
    ext = file_type.lower()
    return os.path.join(Config.UPLOAD_FOLDER, f"{dataset_id}.{ext}")

# -------------------------------------------------------------
# Frontend Routes
# -------------------------------------------------------------

@app.route('/')
def index():
    """Landing Page."""
    return render_template('index.html')

@app.route('/upload')
def upload_page():
    """Upload Page."""
    return render_template('upload.html')

@app.route('/dashboard/<dataset_id>')
def dashboard_page(dataset_id):
    """Main Analytics Dashboard."""
    meta = get_dataset_metadata(dataset_id)
    if not meta:
        return render_template('error.html', 
                               error_title="Dataset Not Found", 
                               error_message=f"No dataset found matching ID '{dataset_id}'."), 404
    return render_template('dashboard.html', dataset=meta)

@app.route('/report/<identifier>')
def report_page(identifier):
    """Report Preview and Download Page (supports both dataset_id and report_id)."""
    dataset_id = identifier
    meta = get_dataset_metadata(dataset_id)
    if not meta:
        rec = get_report_record(identifier)
        if rec:
            dataset_id = rec['dataset_id']
            meta = get_dataset_metadata(dataset_id)

    if not meta:
        return render_template('error.html', 
                               error_title="Dataset Not Found", 
                               error_message="Dataset does not exist."), 404
    
    # Check if a report was already generated
    # If not, generate one automatically for convenience
    file_path = get_dataset_file_path(dataset_id, meta['file_type'])
    report_id = str(uuid.uuid4())[:8]
    pdf_filename = f"DataLens_Report_{dataset_id}.pdf"
    pdf_path = os.path.join(Config.REPORTS_FOLDER, pdf_filename)

    if not os.path.exists(pdf_path):
        df = load_dataset(file_path)
        summary = get_latest_analysis(dataset_id) or get_dataset_overview(df)
        quality = check_data_quality(df)
        ai_res = generate_ai_insights(summary)
        generate_pdf_report(meta, summary, quality, df, ai_res.get('insights', ''), pdf_path)
        save_report_record(report_id, dataset_id, pdf_filename)
        report_meta = {"id": report_id, "filename": pdf_filename}
    else:
        report_meta = {"id": dataset_id, "filename": pdf_filename}

    return render_template('report.html', dataset=meta, report=report_meta)

# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------

@app.route('/api/upload', methods=['POST'])
def api_upload():
    """
    Handle CSV / Excel file uploads.
    Validates file format, size, content, calculates initial overview, and stores in SQLite.
    """
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file uploaded."}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file."}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Please upload a valid CSV or Excel file (.csv, .xlsx, .xls)."}), 400

    try:
        raw_filename = secure_filename(file.filename)
        file_ext = raw_filename.rsplit('.', 1)[1].lower()
        dataset_id = str(uuid.uuid4())[:8]
        save_name = f"{dataset_id}.{file_ext}"
        saved_path = os.path.join(Config.UPLOAD_FOLDER, save_name)
        
        file.save(saved_path)

        # Validate that the file can be parsed and is not empty
        df = load_dataset(saved_path)
        if len(df) == 0:
            os.remove(saved_path)
            return jsonify({"success": False, "error": "The uploaded dataset does not contain usable data."}), 400

        # Calculate dataset statistics & metadata
        overview = get_dataset_overview(df)
        save_dataset_metadata(
            dataset_id=dataset_id,
            filename=raw_filename,
            file_type=file_ext,
            rows=overview['rows'],
            cols=overview['columns'],
            missing=overview['missing_values'],
            duplicates=overview['duplicate_rows']
        )

        # Cache analysis summary
        save_analysis_summary(dataset_id, overview)

        return jsonify({
            "success": True,
            "dataset_id": dataset_id,
            "filename": raw_filename,
            "overview": overview
        }), 201

    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to parse dataset: {str(e)}"}), 500

@app.route('/api/upload-sample', methods=['POST'])
def api_upload_sample():
    """
    Quickly load one of the built-in sample datasets (for viva / presentations).
    """
    data = request.get_json() or {}
    sample_file = data.get('filename', 'student_performance.csv')
    
    # Security: whitelist allowed sample datasets
    allowed_samples = {'student_performance.csv', 'sales_data.csv', 'employee_data.csv'}
    if sample_file not in allowed_samples:
        return jsonify({"success": False, "error": "Invalid sample dataset."}), 400

    src_path = os.path.join(Config.SAMPLE_DATA_FOLDER, sample_file)
    if not os.path.exists(src_path):
        return jsonify({"success": False, "error": "Sample file not found on server."}), 404

    dataset_id = str(uuid.uuid4())[:8]
    dest_path = os.path.join(Config.UPLOAD_FOLDER, f"{dataset_id}.csv")
    shutil.copyfile(src_path, dest_path)

    df = load_dataset(dest_path)
    overview = get_dataset_overview(df)

    save_dataset_metadata(
        dataset_id=dataset_id,
        filename=sample_file,
        file_type="csv",
        rows=overview['rows'],
        cols=overview['columns'],
        missing=overview['missing_values'],
        duplicates=overview['duplicate_rows']
    )
    save_analysis_summary(dataset_id, overview)

    return jsonify({
        "success": True,
        "dataset_id": dataset_id,
        "filename": sample_file
    }), 200

@app.route('/api/dataset/<dataset_id>', methods=['GET'])
def api_get_dataset(dataset_id):
    """Retrieve dataset metadata and top 15 preview rows."""
    meta = get_dataset_metadata(dataset_id)
    if not meta:
        return jsonify({"success": False, "error": "Dataset not found."}), 404

    file_path = get_dataset_file_path(dataset_id, meta['file_type'])
    if not os.path.exists(file_path):
        return jsonify({"success": False, "error": "Underlying data file is missing."}), 404

    df = load_dataset(file_path)
    preview = get_preview(df, max_rows=15)

    return jsonify({
        "success": True,
        "metadata": meta,
        "preview": preview
    }), 200

@app.route('/api/dataset/<dataset_id>/statistics', methods=['GET'])
def api_get_statistics(dataset_id):
    """Retrieve numerical statistics for the dataset."""
    meta = get_dataset_metadata(dataset_id)
    if not meta:
        return jsonify({"success": False, "error": "Dataset not found."}), 404

    file_path = get_dataset_file_path(dataset_id, meta['file_type'])
    df = load_dataset(file_path)
    col_types = detect_column_types(df)
    stats = calculate_numerical_statistics(df, col_types['numeric'])

    return jsonify({
        "success": True,
        "column_types": col_types,
        "statistics": stats
    }), 200

@app.route('/api/dataset/<dataset_id>/quality', methods=['GET'])
def api_get_quality(dataset_id):
    """Audit data quality (missing counts, percentages, unique values, hygiene status)."""
    meta = get_dataset_metadata(dataset_id)
    if not meta:
        return jsonify({"success": False, "error": "Dataset not found."}), 404

    file_path = get_dataset_file_path(dataset_id, meta['file_type'])
    df = load_dataset(file_path)
    quality = check_data_quality(df)
    cleaning = get_cleaning_summary(df)

    return jsonify({
        "success": True,
        "quality": quality,
        "cleaning": cleaning
    }), 200

@app.route('/api/dataset/<dataset_id>/charts', methods=['GET'])
def api_get_charts(dataset_id):
    """Generate responsive Plotly visualizations."""
    meta = get_dataset_metadata(dataset_id)
    if not meta:
        return jsonify({"success": False, "error": "Dataset not found."}), 404

    try:
        file_path = get_dataset_file_path(dataset_id, meta['file_type'])
        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": "Data file not found on disk."}), 404
        df = load_dataset(file_path)
        col_types = detect_column_types(df)
        charts = generate_visualizations(df, col_types)

        return jsonify({
            "success": True,
            "charts": charts
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to generate charts: {str(e)}"}), 500

@app.route('/api/dataset/<dataset_id>/insights', methods=['POST'])
def api_get_insights(dataset_id):
    """Generate or retrieve AI insights for the dataset summary."""
    meta = get_dataset_metadata(dataset_id)
    if not meta:
        return jsonify({"success": False, "error": "Dataset not found."}), 404

    summary = get_latest_analysis(dataset_id)
    if not summary:
        file_path = get_dataset_file_path(dataset_id, meta['file_type'])
        df = load_dataset(file_path)
        summary = get_dataset_overview(df)
        save_analysis_summary(dataset_id, summary)

    result = generate_ai_insights(summary)
    return jsonify(result), 200

@app.route('/api/dataset/<dataset_id>/ask', methods=['POST'])
def api_ask_question(dataset_id):
    """Answer user questions safely using deterministic Pandas calculations."""
    meta = get_dataset_metadata(dataset_id)
    if not meta:
        return jsonify({"success": False, "error": "Dataset not found."}), 404

    req_data = request.get_json() or {}
    question = req_data.get('question', '').strip()
    if not question:
        return jsonify({"success": False, "error": "Question cannot be empty."}), 400

    file_path = get_dataset_file_path(dataset_id, meta['file_type'])
    df = load_dataset(file_path)
    ans = answer_dataset_question(df, question)

    return jsonify({
        "success": True,
        **ans
    }), 200

@app.route('/api/dataset/<dataset_id>/report', methods=['POST'])
def api_generate_report(dataset_id):
    """Generate a ReportLab PDF report and record it in SQLite."""
    meta = get_dataset_metadata(dataset_id)
    if not meta:
        return jsonify({"success": False, "error": "Dataset not found."}), 404

    try:
        file_path = get_dataset_file_path(dataset_id, meta['file_type'])
        df = load_dataset(file_path)
        summary = get_latest_analysis(dataset_id) or get_dataset_overview(df)
        quality = check_data_quality(df)

        ai_res = generate_ai_insights(summary)
        ai_text = ai_res.get('insights', '')

        report_id = str(uuid.uuid4())[:8]
        report_filename = f"DataLens_Report_{dataset_id}.pdf"
        report_path = os.path.join(Config.REPORTS_FOLDER, report_filename)

        generate_pdf_report(meta, summary, quality, df, ai_text, report_path)
        save_report_record(report_id, dataset_id, report_filename)

        return jsonify({
            "success": True,
            "report_id": report_id,
            "filename": report_filename
        }), 201

    except Exception as e:
        return jsonify({"success": False, "error": f"Unable to generate the report: {str(e)}"}), 500

@app.route('/api/report/<report_id>/download', methods=['GET'])
def api_download_report(report_id):
    """Download a generated PDF report."""
    rec = get_report_record(report_id)
    if not rec:
        # Fallback to direct filename check if report_id matches dataset_id
        fallback_filename = f"DataLens_Report_{report_id}.pdf"
        fallback_path = os.path.join(Config.REPORTS_FOLDER, fallback_filename)
        if os.path.exists(fallback_path):
            return send_file(fallback_path, as_attachment=True, download_name=fallback_filename)
        return render_template('error.html', 
                               error_title="Report Not Found", 
                               error_message="The requested PDF report was not found. Please regenerate it."), 404

    pdf_path = os.path.join(Config.REPORTS_FOLDER, rec['filename'])
    if not os.path.exists(pdf_path):
        return render_template('error.html', 
                               error_title="Report File Missing", 
                               error_message="The PDF file is no longer available on disk."), 404

    return send_file(pdf_path, as_attachment=True, download_name=rec['filename'])

# -------------------------------------------------------------
# Global Error Handlers
# -------------------------------------------------------------

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle files exceeding maximum size limit (10MB)."""
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "error": "File size exceeds the 10 MB limit."}), 413
    return render_template('error.html', 
                           error_title="File Too Large", 
                           error_message="The uploaded file exceeds the maximum 10 MB limit."), 413

@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "error": "Endpoint not found."}), 404
    return render_template('error.html', 
                           error_title="Page Not Found", 
                           error_message="The page you requested does not exist."), 404

@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "error": "An internal server error occurred."}), 500
    return render_template('error.html', 
                           error_title="Server Error", 
                           error_message="A server issue occurred while processing your request."), 500

# -------------------------------------------------------------
# Application Runner
# -------------------------------------------------------------

if __name__ == '__main__':
    # Run development server on port 5000
    app.run(host='127.0.0.1', port=5000, debug=True)
