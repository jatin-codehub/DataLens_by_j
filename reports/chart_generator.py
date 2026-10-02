import io
import re
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Headless backend for safe server-side rendering
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Color theme for professional charts
PRIMARY_COLOR = '#2563eb'    # Royal Blue
SECONDARY_COLOR = '#0ea5e9'  # Cyan Blue
ACCENT_COLOR = '#8b5cf6'     # Violet
BAR_COLOR = '#3b82f6'
GRID_COLOR = '#e2e8f0'
TEXT_COLOR = '#1e293b'

def is_id_column(col_name, series):
    """
    Check if a column is likely an identifier (e.g. ID, UUID, Key).
    ID columns should never be used in charts.
    """
    name = str(col_name).lower().strip()
    id_patterns = ['_id', 'id', 'uuid', 'guid', 'key', 'index', 'code', 'order_id', 'student_id', 'employee_id']
    if any(p == name or name.endswith('_id') or name.startswith('id_') for p in id_patterns):
        return True

    # If all values are unique and non-numeric or sequential integers equal to row count
    if len(series) > 5 and series.nunique() == len(series):
        if pd.api.types.is_string_dtype(series) or (pd.api.types.is_integer_dtype(series) and series.min() in [0, 1]):
            return True

    return False

def get_meaningful_numeric_columns(df, numeric_cols):
    """Filter out ID columns and constant columns from numeric columns."""
    meaningful = []
    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) < 2 or series.nunique() <= 1:
            continue
        if not is_id_column(col, series):
            meaningful.append(col)
    return meaningful

def get_meaningful_categorical_columns(df, categorical_cols):
    """Filter out IDs and excessively high/low cardinality columns."""
    meaningful = []
    for col in categorical_cols:
        series = df[col].dropna()
        n_unique = series.nunique()
        # Meaningful categories typically have between 2 and 15 unique values
        if 2 <= n_unique <= 15 and not is_id_column(col, series):
            meaningful.append(col)
    return meaningful

def setup_plot_style():
    """Apply standard clean styling for PDF charts."""
    plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
    plt.rcParams['axes.edgecolor'] = '#cbd5e1'
    plt.rcParams['axes.linewidth'] = 0.8
    plt.rcParams['xtick.color'] = TEXT_COLOR
    plt.rcParams['ytick.color'] = TEXT_COLOR
    plt.rcParams['xtick.labelsize'] = 8.5
    plt.rcParams['ytick.labelsize'] = 8.5
    plt.rcParams['axes.titlesize'] = 10.5
    plt.rcParams['axes.titleweight'] = 'bold'
    plt.rcParams['axes.labelsize'] = 8.5
    plt.rcParams['axes.labelcolor'] = TEXT_COLOR

def generate_histogram(df, col):
    """Generate a clean distribution histogram with mean line."""
    setup_plot_style()
    series = df[col].dropna()
    fig, ax = plt.subplots(figsize=(4.5, 2.5), dpi=220)

    n_bins = min(20, max(6, int(np.sqrt(len(series)))))
    counts, bins, patches = ax.hist(series, bins=n_bins, color=PRIMARY_COLOR, edgecolor='white', alpha=0.85)

    mean_val = series.mean()
    median_val = series.median()
    ax.axvline(mean_val, color='#ef4444', linestyle='--', linewidth=1.2, label=f'Mean: {mean_val:.1f}')
    ax.axvline(median_val, color='#10b981', linestyle=':', linewidth=1.2, label=f'Median: {median_val:.1f}')

    ax.set_title(f'Distribution: {col}', pad=8)
    ax.set_xlabel(col)
    ax.set_ylabel('Frequency')
    ax.grid(axis='y', linestyle='--', alpha=0.6, color=GRID_COLOR)
    ax.set_axisbelow(True)
    ax.legend(frameon=True, facecolor='white', edgecolor='#e2e8f0', fontsize=7.5, loc='upper right')

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=220, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

def generate_bar_chart(df, col):
    """Generate a clean categorical frequency bar chart."""
    setup_plot_style()
    series = df[col].dropna()
    counts = series.value_counts().head(8)

    fig, ax = plt.subplots(figsize=(4.5, 2.5), dpi=220)

    # Use horizontal bars if category names are long or count >= 5
    max_label_len = max([len(str(k)) for k in counts.index]) if len(counts) > 0 else 0
    if max_label_len > 8 or len(counts) >= 5:
        y_pos = range(len(counts))
        ax.barh(y_pos, counts.values, color=BAR_COLOR, edgecolor='none', height=0.65, alpha=0.9)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([str(k)[:15] for k in counts.index])
        ax.invert_yaxis()
        ax.set_xlabel('Count')
        ax.set_ylabel(col)
        ax.grid(axis='x', linestyle='--', alpha=0.6, color=GRID_COLOR)
        # Value annotations
        for i, v in enumerate(counts.values):
            ax.text(v + (max(counts.values) * 0.02), i, str(v), va='center', fontsize=7.5, color=TEXT_COLOR)
    else:
        x_pos = range(len(counts))
        ax.bar(x_pos, counts.values, color=BAR_COLOR, edgecolor='none', width=0.6, alpha=0.9)
        ax.set_xticks(x_pos)
        ax.set_xticklabels([str(k)[:12] for k in counts.index], rotation=15 if max_label_len > 5 else 0)
        ax.set_xlabel(col)
        ax.set_ylabel('Count')
        ax.grid(axis='y', linestyle='--', alpha=0.6, color=GRID_COLOR)
        for i, v in enumerate(counts.values):
            ax.text(i, v + (max(counts.values) * 0.02), str(v), ha='center', fontsize=7.5, color=TEXT_COLOR)

    ax.set_title(f'Count by {col}', pad=8)
    ax.set_axisbelow(True)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=220, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

def generate_scatter_plot(df, x_col, y_col):
    """Generate a clean bivariate scatter plot with trendline."""
    setup_plot_style()
    sub_df = df[[x_col, y_col]].dropna()
    fig, ax = plt.subplots(figsize=(4.5, 2.5), dpi=220)

    ax.scatter(sub_df[x_col], sub_df[y_col], color=ACCENT_COLOR, alpha=0.65, edgecolors='none', s=25)

    # Add trend line if sufficient points and variance
    if len(sub_df) >= 4 and sub_df[x_col].std() > 0:
        try:
            m, b = np.polyfit(sub_df[x_col], sub_df[y_col], 1)
            x_vals = np.linspace(sub_df[x_col].min(), sub_df[x_col].max(), 50)
            ax.plot(x_vals, m * x_vals + b, color='#ef4444', linewidth=1.3, linestyle='--', label='Trend')
            ax.legend(frameon=True, facecolor='white', edgecolor='#e2e8f0', fontsize=7.5, loc='upper left')
        except Exception:
            pass

    ax.set_title(f'{x_col} vs {y_col}', pad=8)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.grid(True, linestyle='--', alpha=0.5, color=GRID_COLOR)
    ax.set_axisbelow(True)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=220, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

def generate_correlation_heatmap(df, num_cols):
    """Generate a compact correlation matrix heatmap."""
    setup_plot_style()
    # Limit to top 6 columns for clean readability
    selected_cols = num_cols[:6]
    corr = df[selected_cols].corr().values

    fig, ax = plt.subplots(figsize=(4.5, 2.5), dpi=220)
    cax = ax.imshow(corr, cmap='Blues', vmin=-1, vmax=1)

    ax.set_xticks(range(len(selected_cols)))
    ax.set_yticks(range(len(selected_cols)))
    ax.set_xticklabels([c[:10] for c in selected_cols], rotation=35, ha='right', fontsize=7.5)
    ax.set_yticklabels([c[:10] for c in selected_cols], fontsize=7.5)

    # Annotate correlation numbers
    for i in range(len(selected_cols)):
        for j in range(len(selected_cols)):
            val = corr[i, j]
            color = 'white' if abs(val) > 0.55 else TEXT_COLOR
            ax.text(j, i, f'{val:.2f}', ha='center', va='center', color=color, fontsize=7.5, fontweight='bold')

    ax.set_title('Correlation Matrix', pad=8)
    fig.colorbar(cax, ax=ax, fraction=0.035, pad=0.03)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=220, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

def generate_time_series_chart(df, date_col, val_col):
    """Generate an aggregated time series line chart."""
    setup_plot_style()
    sub_df = df[[date_col, val_col]].dropna().copy()
    try:
        sub_df[date_col] = pd.to_datetime(sub_df[date_col], errors='coerce')
        sub_df = sub_df.dropna(subset=[date_col]).sort_values(by=date_col)
        # Aggregate by date
        aggregated = sub_df.groupby(sub_df[date_col].dt.date)[val_col].sum()
        if len(aggregated) < 2:
            return None

        fig, ax = plt.subplots(figsize=(4.5, 2.5), dpi=220)
        ax.plot(aggregated.index.astype(str), aggregated.values, color=PRIMARY_COLOR, marker='o', markersize=3, linewidth=1.5)

        ax.set_title(f'{val_col} Over Time', pad=8)
        ax.set_xlabel('Date')
        ax.set_ylabel(val_col)
        ax.grid(True, linestyle='--', alpha=0.5, color=GRID_COLOR)
        ax.set_axisbelow(True)

        # Rotate x labels
        if len(aggregated) > 6:
            n_ticks = min(6, len(aggregated))
            step = max(1, len(aggregated) // n_ticks)
            ax.set_xticks(range(0, len(aggregated), step))
            ax.set_xticklabels([str(aggregated.index[i]) for i in range(0, len(aggregated), step)], rotation=25, ha='right')

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=220, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception:
        return None

def select_useful_charts(df, col_types):
    """
    Intelligently select up to 4 meaningful, non-repetitive charts based on dataset structure.
    Strictly excludes ID columns and applies the 5 Priority Rules.
    Returns:
    List of dicts: [
      {
        'title': ...,
        'xlabel': ...,
        'ylabel': ...,
        'caption': ...,
        'observation': ...,
        'image_buf': io.BytesIO
      }, ...
    ] (Max 4 items)
    """
    charts = []
    numeric_cols = get_meaningful_numeric_columns(df, col_types.get('numeric', []))
    categorical_cols = get_meaningful_categorical_columns(df, col_types.get('categorical', []))
    datetime_cols = col_types.get('datetime', [])

    # Priority 1: Most useful categorical bar chart
    if categorical_cols:
        cat_col = categorical_cols[0]
        buf = generate_bar_chart(df, cat_col)
        top_cat = df[cat_col].value_counts().index[0]
        top_count = df[cat_col].value_counts().iloc[0]
        charts.append({
            'title': f'Category Breakdown: {cat_col}',
            'caption': f'Displays frequency count across {cat_col} categories.',
            'observation': f'The most frequent category is "{top_cat}" with {top_count:,} recorded occurrences.',
            'image_buf': buf
        })

    # Priority 2: Most useful numerical distribution (Histogram)
    if numeric_cols:
        num_col = numeric_cols[0]
        buf = generate_histogram(df, num_col)
        mean_v = df[num_col].mean()
        median_v = df[num_col].median()
        charts.append({
            'title': f'Distribution: {num_col}',
            'caption': f'Histogram showing spread and central tendency of {num_col}.',
            'observation': f'Values center around an average of {mean_v:.2f} (median: {median_v:.2f}).',
            'image_buf': buf
        })

    # Priority 3: Numerical vs Numerical Scatter Plot
    if len(numeric_cols) >= 2 and len(charts) < 4:
        x_c, y_c = numeric_cols[0], numeric_cols[1]
        # Look for pairs that have high correlation if possible
        best_pair = (x_c, y_c)
        if len(numeric_cols) >= 3:
            try:
                corr_mat = df[numeric_cols].corr().abs()
                for c in corr_mat.columns:
                    corr_mat.loc[c, c] = 0
                max_c = corr_mat.stack().idxmax()
                best_pair = (max_c[0], max_c[1])
            except Exception:
                best_pair = (x_c, y_c)

        buf = generate_scatter_plot(df, best_pair[0], best_pair[1])
        r = df[best_pair[0]].corr(df[best_pair[1]])
        direction = "positive" if r > 0.2 else ("negative" if r < -0.2 else "mild")
        charts.append({
            'title': f'{best_pair[0]} vs {best_pair[1]}',
            'caption': f'Bivariate relationship between {best_pair[0]} and {best_pair[1]}.',
            'observation': f'The chart shows a {direction} association (r = {r:.2f}) between {best_pair[0]} and {best_pair[1]} in this sample.',
            'image_buf': buf
        })

    # Priority 4: Time series chart OR Correlation Heatmap OR 2nd distribution
    if len(charts) < 4:
        # Check time series first if date column exists with a numeric column
        time_chart_added = False
        if datetime_cols and numeric_cols:
            buf = generate_time_series_chart(df, datetime_cols[0], numeric_cols[-1])
            if buf is not None:
                charts.append({
                    'title': f'{numeric_cols[-1]} Over Time',
                    'caption': f'Trend of {numeric_cols[-1]} aggregated by {datetime_cols[0]}.',
                    'observation': f'Displays chronological variation of {numeric_cols[-1]} across recorded timestamps.',
                    'image_buf': buf
                })
                time_chart_added = True

        # If no time chart added, check correlation heatmap
        if not time_chart_added and len(numeric_cols) >= 3 and len(charts) < 4:
            buf = generate_correlation_heatmap(df, numeric_cols)
            charts.append({
                'title': 'Feature Correlation Heatmap',
                'caption': 'Pairwise Pearson correlation coefficients across numerical attributes.',
                'observation': 'Highlights linear associations; darker blue indicates higher positive correlation.',
                'image_buf': buf
            })
        elif not time_chart_added and len(numeric_cols) >= 2 and len(charts) < 4:
            # Add second distribution histogram
            num_col2 = numeric_cols[1]
            buf = generate_histogram(df, num_col2)
            charts.append({
                'title': f'Distribution: {num_col2}',
                'caption': f'Histogram showing spread and central tendency of {num_col2}.',
                'observation': f'{num_col2} averages {df[num_col2].mean():.2f} ranging from {df[num_col2].min():.2f} to {df[num_col2].max():.2f}.',
                'image_buf': buf
            })
        elif not time_chart_added and len(categorical_cols) >= 2 and len(charts) < 4:
            # Add second categorical bar chart
            cat_col2 = categorical_cols[1]
            buf = generate_bar_chart(df, cat_col2)
            top_cat2 = df[cat_col2].value_counts().index[0]
            charts.append({
                'title': f'Category Breakdown: {cat_col2}',
                'caption': f'Frequency distribution for {cat_col2}.',
                'observation': f'"{top_cat2}" represents the primary group in {cat_col2}.',
                'image_buf': buf
            })

    # Hard cap at maximum 4 charts
    return charts[:4]
