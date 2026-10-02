import json
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd

# Color palette aligned with modern analytics design system
PRIMARY_COLOR = "#2563EB"    # Accent Blue
SECONDARY_COLOR = "#93C5FD"  # Soft Blue
SUCCESS_COLOR = "#16A34A"    # Green
WARNING_COLOR = "#D97706"    # Amber
TEXT_COLOR = "#172033"
MUTED_TEXT = "#64748B"
GRID_COLOR = "#F1F5F9"
BORDER_COLOR = "#E2E8F0"

PALETTE = [PRIMARY_COLOR, "#3B82F6", "#60A5FA", "#93C5FD", "#1D4ED8", "#1E3A8A"]

def is_id_column(col_name, series):
    """Filter out ID columns that have no analytical meaning in charts."""
    name = str(col_name).lower().strip()
    id_patterns = ['_id', 'id', 'uuid', 'guid', 'key', 'index', 'code', 'order_id', 'student_id', 'employee_id']
    if any(p == name or name.endswith('_id') or name.startswith('id_') for p in id_patterns):
        return True
    if len(series) > 5 and series.nunique() == len(series):
        if pd.api.types.is_string_dtype(series) or (pd.api.types.is_integer_dtype(series) and series.min() in [0, 1]):
            return True
    return False

def generate_visualizations(df, col_types):
    """
    Generate clean, interactive Plotly visualizations based on detected column types.
    Strictly avoids external statsmodels dependencies, filters out ID columns,
    and adheres to restrained, professional UI colors.
    """
    charts = []
    
    # Filter meaningful columns (exclude IDs)
    all_numeric = col_types.get('numeric', [])
    numeric_cols = [c for c in all_numeric if not is_id_column(c, df[c].dropna())]
    if not numeric_cols:
        numeric_cols = all_numeric

    all_categorical = col_types.get('categorical', [])
    categorical_cols = [c for c in all_categorical if not is_id_column(c, df[c].dropna())]
    if not categorical_cols:
        categorical_cols = all_categorical

    standard_layout = dict(
        font=dict(family="Inter, -apple-system, BlinkMacSystemFont, sans-serif", size=12, color=TEXT_COLOR),
        margin=dict(l=40, r=20, t=45, b=40),
        height=320,
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        xaxis=dict(
            gridcolor=GRID_COLOR,
            linecolor=BORDER_COLOR,
            tickcolor=BORDER_COLOR,
            tickfont=dict(size=11, color=MUTED_TEXT),
            title_font=dict(size=12, color=TEXT_COLOR)
        ),
        yaxis=dict(
            gridcolor=GRID_COLOR,
            linecolor=BORDER_COLOR,
            tickcolor=BORDER_COLOR,
            tickfont=dict(size=11, color=MUTED_TEXT),
            title_font=dict(size=12, color=TEXT_COLOR)
        )
    )

    # 1. Numerical Distribution (Histograms - max 2)
    for idx, col in enumerate(numeric_cols[:2]):
        try:
            fig = px.histogram(
                df, 
                x=col,
                title=f"Distribution: {col}",
                template="plotly_white",
                color_discrete_sequence=[PRIMARY_COLOR]
            )
            fig.update_layout(**standard_layout)
            fig.update_layout(bargap=0.08)
            charts.append({
                "id": f"chart_hist_{idx}",
                "title": f"Distribution of {col}",
                "type": "histogram",
                "spec": json.loads(fig.to_json())
            })
        except Exception:
            pass

    # 2. Categorical Distribution (Bar Chart or Donut Chart - max 2)
    for idx, col in enumerate(categorical_cols[:2]):
        try:
            val_counts = df[col].value_counts().reset_index()
            val_counts.columns = [col, 'Count']
            
            if 2 <= len(val_counts) <= 6:
                fig = px.pie(
                    val_counts, 
                    names=col, 
                    values='Count',
                    hole=0.55,
                    title=f"Breakdown by {col}",
                    template="plotly_white",
                    color_discrete_sequence=PALETTE
                )
                fig.update_layout(
                    font=dict(family="Inter, -apple-system, BlinkMacSystemFont, sans-serif", size=12, color=TEXT_COLOR),
                    margin=dict(l=20, r=20, t=45, b=20),
                    height=320,
                    plot_bgcolor="#FFFFFF",
                    paper_bgcolor="#FFFFFF"
                )
            else:
                top_counts = val_counts.head(8)
                fig = px.bar(
                    top_counts, 
                    x=col, 
                    y='Count',
                    title=f"Top Categories: {col}",
                    template="plotly_white",
                    color_discrete_sequence=[PRIMARY_COLOR]
                )
                fig.update_layout(**standard_layout)
                if max([len(str(x)) for x in top_counts[col]]) > 6:
                    fig.update_layout(xaxis_tickangle=-25)

            charts.append({
                "id": f"chart_cat_{idx}",
                "title": f"Category Breakdown: {col}",
                "type": "category",
                "spec": json.loads(fig.to_json())
            })
        except Exception:
            pass

    # 3. Two Numerical Columns Scatter Plot (Safe - No external statsmodels requirement)
    if len(numeric_cols) >= 2:
        try:
            x_col = numeric_cols[0]
            y_col = numeric_cols[1]
            fig = px.scatter(
                df, 
                x=x_col, 
                y=y_col,
                title=f"{x_col} vs {y_col}",
                template="plotly_white",
                color_discrete_sequence=[PRIMARY_COLOR],
                opacity=0.75
            )
            fig.update_traces(marker=dict(size=7, line=dict(width=0.5, color="#FFFFFF")))
            fig.update_layout(**standard_layout)
            charts.append({
                "id": "chart_scatter_1",
                "title": f"{x_col} vs {y_col}",
                "type": "scatter",
                "spec": json.loads(fig.to_json())
            })
        except Exception:
            pass

    # 4. Correlation Heatmap (When 3 or more numerical columns exist)
    if len(numeric_cols) >= 3:
        try:
            selected_num = numeric_cols[:6]
            corr_matrix = df[selected_num].corr().round(2)
            fig = px.imshow(
                corr_matrix,
                text_auto=True,
                title="Correlation Matrix",
                color_continuous_scale="Blues",
                template="plotly_white",
                aspect="auto"
            )
            fig.update_layout(
                font=dict(family="Inter, -apple-system, BlinkMacSystemFont, sans-serif", size=11, color=TEXT_COLOR),
                margin=dict(l=40, r=20, t=45, b=40),
                height=320,
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF"
            )
            charts.append({
                "id": "chart_heatmap_1",
                "title": "Correlation Matrix",
                "type": "heatmap",
                "spec": json.loads(fig.to_json())
            })
        except Exception:
            pass

    return charts
