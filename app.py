import os
import sys
import uuid
import shutil
import tempfile
from pathlib import Path
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file
from werkzeug.utils import secure_filename

from config import Config
from analysis.session_manager import (
    create_session,
    get_session,
    clear_session,
    store_session_report,
    check_and_increment_limit,
    cleanup_expired_sessions
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

# Ensure temporary directory root exists
os.makedirs(Config.TEMP_DIR_ROOT, exist_ok=True)

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

# -------------------------------------------------------------
# Frontend Routes
# -------------------------------------------------------------

@app.route('/')
def index():
    """Landing Page with Privacy-First positioning."""
    cleanup_expired_sessions()
    session_cleared = request.args.get('cleared') == 'true'
    return render_template('index.html', session_cleared=session_cleared)

@app.route('/api/index', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def api_index_fallback():
    """Fallback handler for serverless platform rewrites."""
    return index()

@app.route('/upload')
def upload_page():
    """Upload Page."""
    cleanup_expired_sessions()
    return render_template('upload.html')

@app.route('/privacy')
def privacy_page():
    """Privacy Policy Page."""
    return render_template('privacy.html')

@app.route('/dashboard/<session_id>')
def dashboard_page(session_id):
    """Main Analytics Dashboard with Privacy Session context."""
    cleanup_expired_sessions()
    sess = get_session(session_id)
    if not sess:
        return render_template(
            'error.html', 
            error_title="Dataset Not Found", 
            error_message="Session Expired or Cleared. This temporary session has expired or was cleared. Dataset Not Found. Please upload your dataset again."
        ), 404

    return render_template('dashboard.html', session=sess, dataset=sess)

@app.route('/report/<session_id>')
def report_page(session_id):
    """Report Preview and Download Page."""
    cleanup_expired_sessions()
    sess = get_session(session_id)
    if not sess:
        return render_template(
            'error.html', 
            error_title="Session Expired or Cleared", 
            error_message="The session for this report has expired or was cleared. Please upload your dataset again."
        ), 404

    # Ensure report exists in session temp dir
    pdf_filename = f"DataLens_Report_{session_id[:8]}.pdf"
    pdf_path = os.path.join(sess['temp_dir'], pdf_filename)
    if not os.path.exists(pdf_path):
        summary = sess.get('summary') or get_dataset_overview(sess['df'])
        quality = sess.get('quality') or check_data_quality(sess['df'])
        ai_res = generate_ai_insights(summary)
        generate_pdf_report(sess, summary, quality, sess['df'], ai_res.get('insights', ''), pdf_path)
        store_session_report(session_id, pdf_path)

    report_meta = {"id": session_id, "filename": pdf_filename}
    return render_template('report.html', dataset=sess, session=sess, report=report_meta)

# -------------------------------------------------------------
# REST API Endpoints (Privacy-First, Temporary Sessions)
# -------------------------------------------------------------

@app.route('/api/upload', methods=['POST'])
def api_upload():
    """
    Handle CSV / Excel file uploads into an isolated temporary session.
    Protects against path traversal, oversized files, and stores NO permanent data.
    """
    cleanup_expired_sessions()

    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file uploaded."}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file."}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Please upload a valid CSV or Excel file (.csv, .xlsx, .xls)."}), 400

    # Path traversal protection: sanitize display name and generate safe random internal path
    raw_display_name = secure_filename(file.filename) or "dataset.csv"
    file_ext = raw_display_name.rsplit('.', 1)[1].lower() if '.' in raw_display_name else 'csv'
    
    temp_dir = tempfile.mkdtemp(prefix="dl_upload_", dir=str(Config.TEMP_DIR_ROOT))
    safe_temp_file = os.path.join(temp_dir, f"raw_data.{file_ext}")

    try:
        file.save(safe_temp_file)

        # Validate that the file is not empty and can be parsed
        df = load_dataset(safe_temp_file)
        if len(df) == 0:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return jsonify({"success": False, "error": "The uploaded dataset does not contain usable data."}), 400

        overview = get_dataset_overview(df)
        quality = check_data_quality(df)

        # Create temporary session
        sess = create_session(
            filename=raw_display_name,
            file_type=file_ext,
            df=df,
            temp_dir=temp_dir,
            file_path=safe_temp_file,
            summary=overview,
            quality=quality
        )

        session_id = sess["session_id"]

        return jsonify({
            "success": True,
            "session_id": session_id,
            "dataset_id": session_id,
            "filename": raw_display_name,
            "overview": overview
        }), 201

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"success": False, "error": f"Failed to process dataset: {str(e)}"}), 400

@app.route('/api/upload-sample', methods=['POST'])
def api_upload_sample():
    """
    Load a pre-configured sample dataset into a new isolated temporary session.
    """
    cleanup_expired_sessions()

    data = request.get_json() or {}
    sample_file = data.get('filename', 'student_performance.csv')

    allowed_samples = {'student_performance.csv', 'sales_data.csv', 'employee_data.csv'}
    if sample_file not in allowed_samples:
        return jsonify({"success": False, "error": "Invalid sample dataset."}), 400

    src_path = os.path.join(Config.SAMPLE_DATA_FOLDER, sample_file)
    if not os.path.exists(src_path):
        return jsonify({"success": False, "error": "Sample file not found on server."}), 404

    temp_dir = tempfile.mkdtemp(prefix="dl_sample_", dir=str(Config.TEMP_DIR_ROOT))
    safe_temp_file = os.path.join(temp_dir, sample_file)
    shutil.copyfile(src_path, safe_temp_file)

    try:
        df = load_dataset(safe_temp_file)
        overview = get_dataset_overview(df)
        quality = check_data_quality(df)

        sess = create_session(
            filename=sample_file,
            file_type="csv",
            df=df,
            temp_dir=temp_dir,
            file_path=safe_temp_file,
            summary=overview,
            quality=quality
        )

        session_id = sess["session_id"]

        return jsonify({
            "success": True,
            "session_id": session_id,
            "dataset_id": session_id,
            "filename": sample_file,
            "overview": overview
        }), 200

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"success": False, "error": f"Unable to initialize sample session: {str(e)}"}), 500

@app.route('/api/session/<session_id>/clear', methods=['POST'])
def api_clear_session(session_id):
    """
    Immediately and permanently purge all temporary data and files for a session.
    """
    cleared = clear_session(session_id)
    return jsonify({
        "success": True,
        "cleared": cleared,
        "message": "Session cleared."
    }), 200

@app.route('/api/session/<session_id>/status', methods=['GET'])
def api_session_status(session_id):
    """Check session validity and TTL status."""
    sess = get_session(session_id)
    if not sess:
        return jsonify({"success": False, "error": "Session expired or not found."}), 404

    return jsonify({
        "success": True,
        "session_id": session_id,
        "filename": sess["filename"],
        "active": True
    }), 200

@app.route('/api/dataset/<session_id>', methods=['GET'])
def api_get_dataset(session_id):
    """Retrieve session metadata and top 15 preview rows from temporary session."""
    sess = get_session(session_id)
    if not sess:
        return jsonify({"success": False, "error": "Session expired or invalid. Please upload your dataset again."}), 404

    preview = get_preview(sess["df"], max_rows=15)
    meta = {
        "id": session_id,
        "filename": sess["filename"],
        "file_type": sess["file_type"],
        "rows": sess["rows"],
        "columns": sess["columns"],
        "missing_values": sess["missing_values"],
        "duplicate_rows": sess["duplicate_rows"]
    }

    return jsonify({
        "success": True,
        "metadata": meta,
        "preview": preview
    }), 200

@app.route('/api/dataset/<session_id>/statistics', methods=['GET'])
def api_get_statistics(session_id):
    """Retrieve numerical statistics for the temporary dataset."""
    sess = get_session(session_id)
    if not sess:
        return jsonify({"success": False, "error": "Session expired or invalid. Please upload your dataset again."}), 404

    col_types = detect_column_types(sess["df"])
    stats = calculate_numerical_statistics(sess["df"], col_types['numeric'])

    return jsonify({
        "success": True,
        "column_types": col_types,
        "statistics": stats
    }), 200

@app.route('/api/dataset/<session_id>/quality', methods=['GET'])
def api_get_quality(session_id):
    """Audit data quality (missing counts, percentages, unique values, hygiene status)."""
    sess = get_session(session_id)
    if not sess:
        return jsonify({"success": False, "error": "Session expired or invalid. Please upload your dataset again."}), 404

    quality = sess.get("quality") or check_data_quality(sess["df"])
    cleaning = get_cleaning_summary(sess["df"])

    return jsonify({
        "success": True,
        "quality": quality,
        "cleaning": cleaning
    }), 200

@app.route('/api/dataset/<session_id>/charts', methods=['GET'])
def api_get_charts(session_id):
    """Generate responsive Plotly visualizations."""
    sess = get_session(session_id)
    if not sess:
        return jsonify({"success": False, "error": "Session expired or invalid. Please upload your dataset again."}), 404

    try:
        col_types = detect_column_types(sess["df"])
        charts = generate_visualizations(sess["df"], col_types)

        return jsonify({
            "success": True,
            "charts": charts
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to generate charts: {str(e)}"}), 500

@app.route('/api/dataset/<session_id>/insights', methods=['POST'])
def api_get_insights(session_id):
    """Generate or retrieve AI insights for the dataset summary."""
    sess = get_session(session_id)
    if not sess:
        return jsonify({"success": False, "error": "Session expired or invalid. Please upload your dataset again."}), 404

    # Abuse protection check
    if not check_and_increment_limit(session_id, 'ai'):
        return jsonify({
            "success": False,
            "error": "AI query quota reached for this session to prevent abuse."
        }), 429

    summary = sess.get('summary') or get_dataset_overview(sess["df"])
    result = generate_ai_insights(summary)
    return jsonify(result), 200

@app.route('/api/dataset/<session_id>/ask', methods=['POST'])
def api_ask_question(session_id):
    """Answer user questions safely using deterministic Pandas calculations."""
    sess = get_session(session_id)
    if not sess:
        return jsonify({"success": False, "error": "Session expired or invalid. Please upload your dataset again."}), 404

    # Abuse protection check
    if not check_and_increment_limit(session_id, 'ask'):
        return jsonify({
            "success": False,
            "error": "Query quota reached for this session to prevent abuse."
        }), 429

    req_data = request.get_json() or {}
    question = req_data.get('question', '').strip()
    if not question:
        return jsonify({"success": False, "error": "Question cannot be empty."}), 400

    ans = answer_dataset_question(sess["df"], question)

    return jsonify({
        "success": True,
        **ans
    }), 200

@app.route('/api/dataset/<session_id>/report', methods=['POST'])
def api_generate_report(session_id):
    """Generate a ReportLab PDF report inside the session's temporary directory."""
    sess = get_session(session_id)
    if not sess:
        return jsonify({"success": False, "error": "Session expired or invalid. Please upload your dataset again."}), 404

    try:
        df = sess["df"]
        summary = sess.get('summary') or get_dataset_overview(df)
        quality = sess.get('quality') or check_data_quality(df)

        ai_res = generate_ai_insights(summary)
        ai_text = ai_res.get('insights', '')

        pdf_filename = f"DataLens_Report_{session_id[:8]}.pdf"
        report_path = os.path.join(sess["temp_dir"], pdf_filename)

        generate_pdf_report(sess, summary, quality, df, ai_text, report_path)
        store_session_report(session_id, report_path)

        return jsonify({
            "success": True,
            "session_id": session_id,
            "report_id": session_id,
            "filename": pdf_filename
        }), 201

    except Exception as e:
        return jsonify({"success": False, "error": f"Unable to generate the report: {str(e)}"}), 500

@app.route('/api/report/<session_id>/download', methods=['GET'])
def api_download_report(session_id):
    """Download a generated PDF report from the session's temporary storage."""
    sess = get_session(session_id)
    if not sess:
        return render_template(
            'error.html', 
            error_title="Report Not Found", 
            error_message="The session for this report has expired or was cleared. Please upload your dataset again."
        ), 404

    report_path = sess.get('report_path')
    if not report_path or not os.path.exists(report_path):
        # Auto-generate if missing
        try:
            pdf_filename = f"DataLens_Report_{session_id[:8]}.pdf"
            report_path = os.path.join(sess["temp_dir"], pdf_filename)
            summary = sess.get('summary') or get_dataset_overview(sess["df"])
            quality = sess.get('quality') or check_data_quality(sess["df"])
            ai_res = generate_ai_insights(summary)
            generate_pdf_report(sess, summary, quality, sess["df"], ai_res.get('insights', ''), report_path)
            store_session_report(session_id, report_path)
        except Exception as e:
            return render_template(
                'error.html', 
                error_title="Report Generation Failed", 
                error_message=f"Could not build report: {str(e)}"
            ), 500

    return send_file(report_path, as_attachment=True, download_name=os.path.basename(report_path))

# -------------------------------------------------------------
# Global Error Handlers (Predictable JSON for API, HTML for Web)
# -------------------------------------------------------------

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle files exceeding maximum size limit."""
    limit_mb = Config.MAX_UPLOAD_MB
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "error": f"File size exceeds the {limit_mb} MB limit."}), 413
    return render_template(
        'error.html', 
        error_title="File Too Large", 
        error_message=f"The uploaded file exceeds the maximum {limit_mb} MB limit."
    ), 413

@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "error": "Endpoint not found."}), 404
    return render_template(
        'error.html', 
        error_title="Page Not Found", 
        error_message="The page you requested does not exist or your temporary session has expired."
    ), 404

@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "error": "An internal server error occurred."}), 500
    return render_template(
        'error.html', 
        error_title="Server Error", 
        error_message="A server issue occurred while processing your request."
    ), 500

# -------------------------------------------------------------
# Application Runner
# -------------------------------------------------------------

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
