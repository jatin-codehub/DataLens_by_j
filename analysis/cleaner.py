import pandas as pd

def check_data_quality(df):
    """
    Audit data quality across all columns in the DataFrame:
    - Missing value count
    - Missing percentage
    - Number of unique values
    - Column data type
    - Health classification: Good (0%), Warning (<10%), Needs Attention (>=10%)
    """
    total_rows = len(df)
    quality_report = []

    for col in df.columns:
        missing_count = int(df[col].isnull().sum())
        missing_pct = round((missing_count / total_rows * 100), 2) if total_rows > 0 else 0.0
        unique_count = int(df[col].nunique(dropna=True))
        dtype_str = str(df[col].dtype)

        if missing_pct == 0:
            status = "Good"
            badge = "success"
        elif missing_pct < 10.0:
            status = "Warning"
            badge = "warning"
        else:
            status = "Needs Attention"
            badge = "danger"

        quality_report.append({
            "column": col,
            "data_type": dtype_str,
            "missing": missing_count,
            "missing_pct": missing_pct,
            "unique": unique_count,
            "status": status,
            "badge": badge
        })

    return quality_report

def get_cleaning_summary(df):
    """
    Inspect duplicate rows and completely empty columns.
    Reports what cleaning would do without mutating the underlying data silently.
    """
    total_rows = len(df)
    duplicate_count = int(df.duplicated().sum())
    empty_cols = [col for col in df.columns if df[col].isnull().all()]

    return {
        "original_rows": total_rows,
        "duplicate_rows": duplicate_count,
        "clean_rows_estimate": total_rows - duplicate_count,
        "empty_columns": empty_cols,
        "has_duplicates": duplicate_count > 0,
        "has_empty_cols": len(empty_cols) > 0
    }
