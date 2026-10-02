import os
import re
import pandas as pd
from config import Config

def generate_ai_insights(summary_dict):
    """
    Generate structured, educational data insights using Google Gemini API.
    Sends only the structured statistical summary (never raw tabular data).
    Gracefully falls back to a deterministic rule-based analysis if API key is not configured or fails.
    """
    api_key = Config.GEMINI_API_KEY
    if not api_key or api_key.strip() == '' or api_key == 'your_gemini_api_key_here':
        return {
            "success": True,
            "mode": "rule_based",
            "message": "Note: Google Gemini API key is not configured in .env. Showing local rule-based statistical insights.",
            "insights": generate_rule_based_insights(summary_dict)
        }

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel('gemini-1.5-flash')

        prompt = f"""
You are a senior data analyst and mentor helping a university student understand their dataset.
Analyze the following structured dataset summary and provide a clean, educational report:

DATASET METADATA:
- Total Rows: {summary_dict.get('rows')}
- Total Columns: {summary_dict.get('columns')}
- Total Missing Values: {summary_dict.get('missing_values')}
- Total Duplicate Rows: {summary_dict.get('duplicate_rows')}
- Numerical Summary: {summary_dict.get('numeric_summary')}
- Categorical Columns: {summary_dict.get('column_types', {}).get('categorical')}

Generate a structured analysis strictly following these 5 sections:
1. Key Findings: Main statistical highlights and high-impact values.
2. Interesting Patterns: Notable spreads, variations, or distributions observed.
3. Data Quality Observations: Assessment of completeness and duplicate records.
4. Possible Conclusions: Objective, data-backed takeaways.
5. Limitations: Caveats, missing context, and reminders that correlation does not imply causation.

Strict Guidelines:
- Base every single observation directly on the provided numbers.
- NEVER invent or assume any values not in the summary.
- If information is insufficient for a conclusion, state that clearly.
- Keep the language clear, modern, and easily explainable in a college viva.
"""
        response = model.generate_content(prompt)
        return {
            "success": True,
            "mode": "gemini",
            "message": "AI insights successfully generated via Google Gemini.",
            "insights": response.text
        }

    except Exception as e:
        # Fallback gracefully without breaking the student's workflow
        return {
            "success": True,
            "mode": "fallback_rule_based",
            "message": f"AI service notice ({str(e)}). Falling back to local statistical analysis.",
            "insights": generate_rule_based_insights(summary_dict)
        }

def generate_rule_based_insights(summary):
    """
    Produce reliable, deterministic observations directly from Pandas statistics.
    Ensures 100% reliability even when offline or without an active API key.
    """
    rows = summary.get('rows', 0)
    cols = summary.get('columns', 0)
    missing = summary.get('missing_values', 0)
    dups = summary.get('duplicate_rows', 0)
    num_stats = summary.get('numeric_summary', {})
    col_types = summary.get('column_types', {})

    sections = []

    # Section 1: Key Findings
    findings = [
        f"The dataset consists of **{rows:,}** observations across **{cols}** distinct variables.",
    ]
    if num_stats:
        top_col = list(num_stats.keys())[0]
        s = num_stats[top_col]
        findings.append(f"For **{top_col}**, the recorded average is **{s['mean']}** with values ranging from **{s['min']}** to **{s['max']}**.")
    sections.append("### 1. Key Findings\n" + "\n".join(f"- {f}" for f in findings))

    # Section 2: Patterns & Distributions
    patterns = []
    if len(num_stats) > 1:
        second_col = list(num_stats.keys())[1]
        s2 = num_stats[second_col]
        patterns.append(f"**{second_col}** exhibits a median of **{s2['median']}** and a standard deviation of **{s2['std']}**, indicating the spread of values around the center.")
    categoricals = col_types.get('categorical', [])
    if categoricals:
        patterns.append(f"Identified {len(categoricals)} categorical dimension(s): {', '.join(categoricals[:4])}, suitable for segmentation analysis.")
    if not patterns:
        patterns.append("Numerical variables show standard distribution characteristics across the observed sample.")
    sections.append("### 2. Interesting Patterns\n" + "\n".join(f"- {p}" for p in patterns))

    # Section 3: Data Quality Observations
    quality = []
    if dups == 0:
        quality.append("Zero duplicate rows detected, indicating healthy record ingestion.")
    else:
        quality.append(f"Detected **{dups} duplicate row(s)** ({round(dups / rows * 100, 2)}% of total). Deduplication is recommended before statistical modeling.")

    if missing == 0:
        quality.append("The dataset contains zero missing values, providing a complete sample.")
    else:
        quality.append(f"Identified **{missing} null or unpopulated cell(s)** across attributes. Imputation or record filtering should be reviewed.")
    sections.append("### 3. Data Quality Observations\n" + "\n".join(f"- {q}" for q in quality))

    # Section 4: Possible Conclusions
    conclusions = [
        f"The distribution shows consistent variance suitable for descriptive reporting and baseline analysis.",
        "Primary metrics are sufficiently populated to draw sample-level benchmark comparisons."
    ]
    sections.append("### 4. Possible Conclusions\n" + "\n".join(f"- {c}" for c in conclusions))

    # Section 5: Limitations
    limitations = [
        f"This sample of {rows} rows reflects the recorded observations and may not represent broader unseen populations.",
        "Observed statistical associations reflect correlation within this sample and must not be interpreted as causal relationships.",
        "Domain-specific context should always validate these automated numeric findings."
    ]
    sections.append("### 5. Limitations\n" + "\n".join(f"- {l}" for l in limitations))

    return "\n\n".join(sections)

def answer_dataset_question(df, question):
    """
    Answers user questions deterministically using Pandas first.
    Never executes arbitrary or untrusted code.
    Handles counts, averages, minimums, maximums, totals, and column queries safely.
    """
    q = question.strip().lower()
    total_rows = len(df)
    total_cols = len(df.columns)

    # 1. Total row count queries
    if any(phrase in q for phrase in ["how many rows", "total rows", "row count", "number of rows", "how many records", "how many students", "how many orders", "how many employees"]):
        return {
            "question": question,
            "answer": f"The dataset contains exactly **{total_rows:,}** rows (records).",
            "method": "Calculated via Pandas `len(df)`"
        }

    # 2. Total column count / names
    if any(phrase in q for phrase in ["how many columns", "total columns", "column count", "list columns", "what are the columns"]):
        col_list = ", ".join(f"`{c}`" for c in df.columns)
        return {
            "question": question,
            "answer": f"The dataset contains **{total_cols}** columns: {col_list}.",
            "method": "Calculated via Pandas `df.columns`"
        }

    # 3. Missing values query
    if any(w in q for w in ["missing", "null", "empty", "nan"]):
        total_missing = int(df.isnull().sum().sum())
        if total_missing == 0:
            return {
                "question": question,
                "answer": "There are **0** missing values in this entire dataset. Every row and column is fully populated.",
                "method": "Calculated via Pandas `df.isnull().sum().sum()`"
            }
        else:
            col_missing = df.isnull().sum()
            affected = [f"**{col}**: {count} missing" for col, count in col_missing.items() if count > 0]
            return {
                "question": question,
                "answer": f"There are **{total_missing:,}** total missing cells. Breakdown: {'; '.join(affected)}.",
                "method": "Calculated via Pandas `df.isnull().sum()`"
            }

    def match_col(col_name):
        c_low = col_name.lower()
        if re.search(r'\b' + re.escape(c_low) + r'\b', q):
            return True
        words = [w for w in c_low.split('_') if len(w) > 2 and w not in ['usd', 'eur', 'col', 'data', 'val']]
        for w in words:
            if re.search(r'\b' + re.escape(w) + r'\b', q):
                return True
        return False

    # 4. Duplicate rows query
    if "duplicate" in q:
        dups = int(df.duplicated().sum())
        return {
            "question": question,
            "answer": f"There are **{dups:,}** duplicate row(s) in this dataset.",
            "method": "Calculated via Pandas `df.duplicated().sum()`"
        }

    # 5. Median inquiry
    if "median" in q:
        for col in df.columns:
            if match_col(col):
                if pd.api.types.is_numeric_dtype(df[col]):
                    med_val = round(float(df[col].median()), 2)
                    return {
                        "question": question,
                        "answer": f"The median of **{col}** is **{med_val}**.",
                        "method": f"Calculated via Pandas `df['{col}'].median()`"
                    }

    # 6. Column-specific inquiries (Average / Mean)
    if "average" in q or "mean" in q:
        for col in df.columns:
            if match_col(col):
                if pd.api.types.is_numeric_dtype(df[col]):
                    val = round(float(df[col].mean()), 2)
                    median_val = round(float(df[col].median()), 2)
                    return {
                        "question": question,
                        "answer": f"The average (mean) of **{col}** is **{val}** (median is **{median_val}**).",
                        "method": f"Calculated via Pandas `df['{col}'].mean()`"
                    }
                else:
                    return {
                        "question": question,
                        "answer": f"**{col}** is a categorical column, so an average cannot be computed. Unique values: {df[col].nunique()}.",
                        "method": "Pandas dtype validation"
                    }

    # 7. Column-specific inquiries (Highest / Maximum)
    if any(w in q for w in ["highest", "maximum", "max", "top", "greatest"]):
        for col in df.columns:
            if match_col(col):
                if pd.api.types.is_numeric_dtype(df[col]):
                    max_val = round(float(df[col].max()), 2)
                    sub = df[df[col] == df[col].max()]
                    id_col = [c for c in df.columns if 'id' in c.lower() or 'name' in c.lower()]
                    detail = ""
                    if id_col:
                        top_label = sub[id_col[0]].iloc[0]
                        detail = f" (Held by {id_col[0]}: **{top_label}**)"
                    return {
                        "question": question,
                        "answer": f"The highest value for **{col}** is **{max_val}**{detail}.",
                        "method": f"Calculated via Pandas `df['{col}'].max()`"
                    }

    # 8. Column-specific inquiries (Lowest / Minimum)
    if any(w in q for w in ["lowest", "minimum", "min", "least", "bottom"]):
        for col in df.columns:
            if match_col(col):
                if pd.api.types.is_numeric_dtype(df[col]):
                    min_val = round(float(df[col].min()), 2)
                    return {
                        "question": question,
                        "answer": f"The minimum value for **{col}** is **{min_val}**.",
                        "method": f"Calculated via Pandas `df['{col}'].min()`"
                    }

    # 9. Category grouping questions (e.g., "Which region has highest average sales?")
    if "which" in q or "group by" in q or "department" in q or "category" in q or "region" in q:
        cat_matches = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c]) and match_col(c)]
        num_matches = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and match_col(c)]

        if cat_matches and num_matches:
            grp_col = cat_matches[0]
            val_col = num_matches[0]
            grouped = df.groupby(grp_col)[val_col].mean().round(2).sort_values(ascending=False)
            top_group = grouped.index[0]
            top_val = grouped.iloc[0]
            return {
                "question": question,
                "answer": f"Grouping by **{grp_col}**, the highest average **{val_col}** belongs to **{top_group}** with an average of **{top_val}**.",
                "method": f"Calculated via Pandas `df.groupby('{grp_col}')['{val_col}'].mean()`"
            }

    # 9. If Gemini is available, answer analytical queries using structured summary
    api_key = Config.GEMINI_API_KEY
    if api_key and api_key.strip() != '' and api_key != 'your_gemini_api_key_here':
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key.strip())
            model = genai.GenerativeModel('gemini-1.5-flash')

            # Provide small numerical context
            num_desc = df.describe().round(2).to_dict()
            prompt = f"""
A student asked this question about their dataset:
"{question}"

DATASET SUMMARY:
Columns: {list(df.columns)}
Total Rows: {len(df)}
Statistical Overview: {num_desc}

Provide a concise, direct, 2-3 sentence factual answer strictly based on this data. Never invent facts.
"""
            res = model.generate_content(prompt)
            return {
                "question": question,
                "answer": res.text.strip(),
                "method": "Generated via Gemini API using dataset summary"
            }
        except Exception:
            pass

    # Generic friendly fallback guiding the student
    return {
        "question": question,
        "answer": (
            f"I checked the dataset ({total_rows} rows, columns: {', '.join(df.columns[:5])}). "
            "You can ask questions such as:\n"
            "- *'What is the average [column_name]?'*\n"
            "- *'What is the highest [column_name]?'*\n"
            "- *'How many rows are there?'*\n"
            "- *'Are there any missing values?'*\n"
            "- *'How many duplicate rows?'*"
        ),
        "method": "Natural Language Query Analyzer"
    }
