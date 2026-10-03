import re
import pandas as pd
import numpy as np

def is_identifier_column(col_name, series):
    """
    Check if a column is likely an identifier (e.g. ID, UUID, Key).
    Prevents Transaction_ID, Customer_ID, etc. from being classified as analytical categories.
    """
    name = str(col_name).lower().strip()
    id_patterns = [
        'id', 'uuid', 'guid', 'key', 'index', 'code', 'token',
        'order_id', 'student_id', 'employee_id', 'transaction_id', 'customer_id'
    ]
    if name in id_patterns or name.endswith('_id') or name.startswith('id_') or name.endswith('id'):
        return True

    # If series is non-empty and every value is unique and non-numeric or sequential
    non_null = series.dropna()
    if len(non_null) > 5 and non_null.nunique() == len(non_null):
        if pd.api.types.is_string_dtype(non_null) or (pd.api.types.is_integer_dtype(non_null) and non_null.min() in [0, 1]):
            return True

    return False

def load_dataset(file_path):
    """
    Load a CSV or Excel file into a Pandas DataFrame.
    Safely handles encodings, deduplicates column names, and validates content.
    Raises ValueError if file format is unsupported or file is empty.
    """
    path_str = str(file_path).lower()
    df = None

    if path_str.endswith('.csv'):
        encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
        for enc in encodings:
            try:
                df = pd.read_csv(file_path, encoding=enc)
                break
            except (UnicodeDecodeError, Exception):
                continue
        if df is None:
            raise ValueError("Unable to decode CSV file with supported encodings (UTF-8, Latin1, CP1252).")
    elif path_str.endswith(('.xlsx', '.xls')):
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            raise ValueError(f"Unable to read Excel file: {str(e)}")
    else:
        raise ValueError("Unsupported file format. Please upload a CSV (.csv) or Excel (.xlsx, .xls) file.")

    if df is None or len(df.columns) == 0:
        raise ValueError("The uploaded dataset contains no columns.")

    # Deduplicate column names if duplicates exist
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique():
        dup_indices = cols[cols == dup].index.values
        for i, idx in enumerate(dup_indices[1:], start=1):
            cols[idx] = f"{dup}_{i}"
    df.columns = cols

    return df

def detect_column_types(df):
    """
    Detect granular column types:
    - numeric
    - categorical
    - datetime
    - identifier
    - text
    - boolean
    """
    raw_numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = []
    identifier_cols = []
    datetime_cols = []
    boolean_cols = []
    text_cols = []
    categorical_cols = []

    for col in df.columns:
        series = df[col]
        non_null = series.dropna()

        # 1. Identifier check
        if is_identifier_column(col, series):
            identifier_cols.append(col)
            continue

        # 2. Boolean check
        if pd.api.types.is_bool_dtype(series):
            boolean_cols.append(col)
            continue
        if len(non_null) > 0 and non_null.nunique() <= 2:
            unique_vals = set(str(v).lower().strip() for v in non_null.unique())
            if unique_vals.issubset({'true', 'false', '0', '1', 'yes', 'no', 't', 'f'}):
                boolean_cols.append(col)
                continue

        # 3. Numeric check
        if col in raw_numeric_cols:
            numeric_cols.append(col)
            continue

        # 4. Datetime check
        if pd.api.types.is_datetime64_any_dtype(series):
            datetime_cols.append(col)
            continue
        if len(non_null) > 0 and non_null.dtype == 'object':
            try:
                sample = non_null.head(25)
                parsed = pd.to_datetime(sample, errors='coerce')
                if parsed.notnull().sum() / len(sample) >= 0.8:
                    datetime_cols.append(col)
                    continue
            except Exception:
                pass

        # 5. Text vs Categorical check
        if len(non_null) > 0:
            avg_len = non_null.astype(str).str.len().mean()
            n_unique = non_null.nunique()
            # If text is long sentences/descriptions or very high unique count
            if avg_len > 40 or (n_unique > 30 and n_unique > len(non_null) * 0.5):
                text_cols.append(col)
                continue

        # 6. Default to categorical
        categorical_cols.append(col)

    return {
        "numeric": numeric_cols,
        "categorical": categorical_cols,
        "datetime": datetime_cols,
        "identifier": identifier_cols,
        "text": text_cols,
        "boolean": boolean_cols
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
    preview_df = df.head(max_rows).copy()
    columns = [
        {"name": col, "dtype": str(df[col].dtype)}
        for col in df.columns
    ]
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
