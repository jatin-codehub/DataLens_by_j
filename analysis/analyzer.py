import pandas as pd
import numpy as np

def load_dataset(file_path):
    """
    Load a CSV or Excel file into a Pandas DataFrame.
    Raises ValueError if file format is unsupported.
    """
    if file_path.endswith('.csv'):
        # Attempt UTF-8, then fallback to latin1 for resilient reading
        try:
            return pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding='latin1')
    elif file_path.endswith(('.xlsx', '.xls')):
        return pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file format. Please upload a CSV or Excel file.")

def detect_column_types(df):
    """
    Detect column types: Numerical, Categorical, or Datetime.
    Returns a dictionary of categorized column names.
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    datetime_cols = []
    categorical_cols = []

    for col in df.columns:
        if col in numeric_cols:
            continue

        # Check if the column can be safely parsed as datetime
        non_null = df[col].dropna()
        if len(non_null) > 0 and non_null.dtype == 'object':
            try:
                sample = non_null.head(20)
                parsed = pd.to_datetime(sample, errors='coerce')
                # If at least 80% of non-null samples parse as dates and isn't purely numeric
                if parsed.notnull().sum() / len(sample) >= 0.8:
                    datetime_cols.append(col)
                    continue
            except Exception:
                pass

        categorical_cols.append(col)

    return {
        "numeric": numeric_cols,
        "categorical": categorical_cols,
        "datetime": datetime_cols
    }

def calculate_numerical_statistics(df, numeric_cols):
    """
    Calculate statistical measures for each numerical column:
    Count, Mean, Median, Min, Max, Standard Deviation.
    """
    stats = {}
    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) == 0:
            continue
        
        mean_val = float(series.mean())
        median_val = float(series.median())
        min_val = float(series.min())
        max_val = float(series.max())
        std_val = float(series.std()) if len(series) > 1 else 0.0

        stats[col] = {
            "count": int(series.count()),
            "mean": round(mean_val, 2),
            "median": round(median_val, 2),
            "min": round(min_val, 2),
            "max": round(max_val, 2),
            "std": round(std_val, 2)
        }
    return stats

def get_preview(df, max_rows=15):
    """
    Extract top rows and column information for the UI preview table.
    """
    # Replace NaN with None so JSON serialization outputs null
    preview_df = df.head(max_rows).copy()
    columns = [
        {"name": col, "dtype": str(df[col].dtype)}
        for col in df.columns
    ]
    # Convert DataFrame records to python dicts safely
    rows = preview_df.replace({np.nan: None}).to_dict(orient='records')
    return {
        "columns": columns,
        "rows": rows,
        "total_previewed": len(rows),
        "total_rows": len(df)
    }

def get_dataset_overview(df):
    """
    Compile high-level summary of rows, columns, missing values, duplicates,
    column categorization, and descriptive statistics.
    """
    col_types = detect_column_types(df)
    numeric_stats = calculate_numerical_statistics(df, col_types['numeric'])
    
    total_missing = int(df.isnull().sum().sum())
    total_duplicates = int(df.duplicated().sum())

    return {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "missing_values": total_missing,
        "duplicate_rows": total_duplicates,
        "column_types": col_types,
        "numeric_summary": numeric_stats
    }
