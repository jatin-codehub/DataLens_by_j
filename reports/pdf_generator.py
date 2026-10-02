import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reports.chart_generator import select_useful_charts, is_id_column

def extract_concise_key_insights(df, summary_dict, dataset_meta):
    """
    Generate 3-5 concise, strictly data-supported bullet points with actual numbers.
    Never generates vague or generic statements.
    """
    bullets = []
    rows = dataset_meta.get('rows', len(df))
    cols = dataset_meta.get('columns', len(df.columns))
    missing = dataset_meta.get('missing_values', 0)
    dups = dataset_meta.get('duplicate_rows', 0)
    num_stats = summary_dict.get('numeric_summary', {})

    # 1. Scale bullet
    bullets.append(f"<b>Dataset Dimensions:</b> Contains <b>{rows:,}</b> total records across <b>{cols}</b> attributes.")

    # 2. Key numerical metrics (top 2 meaningful columns)
    meaningful_num = [c for c in num_stats.keys() if not is_id_column(c, df[c].dropna())]
    for col in meaningful_num[:2]:
        s = num_stats[col]
        bullets.append(f"<b>{col}:</b> Averages <b>{s['mean']:,.2f}</b> (median: {s['median']:,.2f}), ranging from {s['min']:,.2f} to {s['max']:,.2f}.")

    # 3. Data hygiene bullets
    if missing == 0:
        bullets.append("<b>Completeness:</b> No missing values detected across any column (100% complete records).")
    else:
        bullets.append(f"<b>Missing Values:</b> Found <b>{missing:,}</b> unpopulated cells requiring review.")

    if dups == 0:
        bullets.append("<b>Cleanliness:</b> Zero duplicate rows detected in this sample.")
    else:
        bullets.append(f"<b>Duplicates:</b> Detected <b>{dups:,}</b> duplicate rows ({dups/rows*100:.1f}% of total).")

    return bullets[:5]

def format_clean_ai_insights(ai_text, summary_dict, df):
    """
    Format up to 5 short, evidence-based AI / analytical insights.
    Strips generic boilerplates like 'consistent variance' or 'further ML can proceed'.
    """
    insights = []
    if ai_text:
        # Extract meaningful bullet points
        raw_lines = ai_text.split('\n')
        for line in raw_lines:
            line = line.strip()
            # Ignore headers and generic filler
            if not line or line.startswith('#') or any(w in line.lower() for w in [
                'consistent variance', 'sufficiently populated', 'further machine learning',
                'hypothesis testing can proceed', 'possible conclusions', 'interesting patterns'
            ]):
                continue
            # Strip bullet prefixes
            clean_line = line.lstrip('*-•0123456789. ')
            if len(clean_line) > 15:
                insights.append(clean_line)
            if len(insights) >= 5:
                break

    # Fallback to factual calculated statements if needed
    if len(insights) < 3:
        num_stats = summary_dict.get('numeric_summary', {})
        for col, s in list(num_stats.items())[:3]:
            if not is_id_column(col, df[col].dropna()):
                insights.append(f"{col} exhibits a mean of {s['mean']:,.2f} with values spanning {s['min']:,.2f} to {s['max']:,.2f}.")

    return insights[:5]

def generate_pdf_report(dataset_meta, summary_dict, quality_report, df, ai_insights_text, output_path):
    """
    Build a clean, visual, professional ReportLab PDF report.
    Structure:
    Page 1: Executive Summary (Header, 4-5 Metric Cards, Key Insights, Sample Preview)
    Page 2: Statistical Summary (Compact Table) & Useful Charts (Actual High-Res Images)
    Page 3: Additional Charts, Compact Data Quality, AI Insights, Limitations, Conclusion
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    story = []

    # Typography & Palette
    COLOR_PRIMARY = colors.HexColor('#2563eb')
    COLOR_DARK = colors.HexColor('#0f172a')
    COLOR_MUTED = colors.HexColor('#64748b')
    COLOR_BORDER = colors.HexColor('#e2e8f0')
    COLOR_CARD_BG = colors.HexColor('#f8fafc')
    COLOR_OBS_BG = colors.HexColor('#eff6ff')

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=COLOR_DARK,
        spaceAfter=2
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=COLOR_MUTED,
        spaceAfter=10
    )
    section_heading = ParagraphStyle(
        'SecHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=COLOR_PRIMARY,
        spaceBefore=10,
        spaceAfter=5
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=COLOR_DARK
    )
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=COLOR_DARK,
        leftIndent=12,
        firstLineIndent=-12,
        spaceAfter=3
    )
    card_num_style = ParagraphStyle(
        'CardNum',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=16,
        textColor=COLOR_PRIMARY,
        alignment=1
    )
    card_label_style = ParagraphStyle(
        'CardLabel',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=COLOR_MUTED,
        alignment=1
    )
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=COLOR_DARK
    )
    table_head = ParagraphStyle(
        'TableHead',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=colors.white
    )
    chart_obs_style = ParagraphStyle(
        'ChartObs',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#1e40af')
    )

    # ---------------------------------------------------------
    # PAGE 1: EXECUTIVE SUMMARY
    # ---------------------------------------------------------
    story.append(Paragraph("DataLens — Data Analysis Report", title_style))
    analysis_date = datetime.now().strftime("%B %d, %Y &bull; %I:%M %p")
    story.append(Paragraph(
        f"<b>Dataset:</b> {dataset_meta.get('filename')} &nbsp;|&nbsp; "
        f"<b>Type:</b> {dataset_meta.get('file_type', 'CSV').upper()} &nbsp;|&nbsp; "
        f"<b>Analysis Date:</b> {analysis_date}",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_PRIMARY, spaceAfter=8))

    # 4-5 Large Visual Metric Cards
    rows_val = dataset_meta.get('rows', len(df))
    cols_val = dataset_meta.get('columns', len(df.columns))
    missing_val = dataset_meta.get('missing_values', 0)
    dups_val = dataset_meta.get('duplicate_rows', 0)
    col_types = summary_dict.get('column_types', {})
    num_col_count = len(col_types.get('numeric', []))
    cat_col_count = len(col_types.get('categorical', []))

    # Adaptive 5th card: if numeric exist, show numeric; otherwise show categorical
    fifth_val = f"{num_col_count} Numeric" if num_col_count > 0 else f"{cat_col_count} Categorical"
    fifth_label = "Numerical Fields" if num_col_count > 0 else "Categorical Fields"

    cards_data = [
        [
            Paragraph(f"<b>{rows_val:,}</b>", card_num_style),
            Paragraph(f"<b>{cols_val}</b>", card_num_style),
            Paragraph(f"<b>{missing_val:,}</b>", card_num_style),
            Paragraph(f"<b>{dups_val:,}</b>", card_num_style),
            Paragraph(f"<b>{fifth_val}</b>", card_num_style),
        ],
        [
            Paragraph("Total Records", card_label_style),
            Paragraph("Total Columns", card_label_style),
            Paragraph("Missing Values", card_label_style),
            Paragraph("Duplicate Rows", card_label_style),
            Paragraph(fifth_label, card_label_style),
        ]
    ]
    t_cards = Table(cards_data, colWidths=[108, 108, 108, 108, 108])
    t_cards.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_CARD_BG),
        ('BOX', (0,0), (0,-1), 0.8, COLOR_BORDER),
        ('BOX', (1,0), (1,-1), 0.8, COLOR_BORDER),
        ('BOX', (2,0), (2,-1), 0.8, COLOR_BORDER),
        ('BOX', (3,0), (3,-1), 0.8, COLOR_BORDER),
        ('BOX', (4,0), (4,-1), 0.8, COLOR_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_cards)
    story.append(Spacer(1, 8))

    # Key Insights (3-5 short bullet points)
    story.append(Paragraph("Key Insights", section_heading))
    key_insights = extract_concise_key_insights(df, summary_dict, dataset_meta)
    for ki in key_insights:
        story.append(Paragraph(f"&bull; {ki}", bullet_style))
    story.append(Spacer(1, 8))

    # Dataset Preview (Small: 5 rows x 6-8 representative columns)
    story.append(Paragraph("Dataset Preview", section_heading))
    story.append(Paragraph("<i>Showing a sample of the uploaded dataset.</i>", subtitle_style))

    # Select representative columns (skip high-entropy IDs if > 7 cols)
    preview_cols = [c for c in df.columns if not is_id_column(c, df[c].dropna())]
    if len(preview_cols) < 5:
        preview_cols = list(df.columns)
    preview_cols = preview_cols[:7]

    col_w = 540 / max(len(preview_cols), 1)
    preview_table_data = [
        [Paragraph(f"<b>{c}</b>", table_head) for c in preview_cols]
    ]
    for row in df[preview_cols].head(5).fillna('-').values.tolist():
        preview_table_data.append([
            Paragraph(str(val)[:18], table_cell) for val in row
        ])

    t_preview = Table(preview_table_data, colWidths=[col_w] * len(preview_cols))
    t_preview.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_CARD_BG]),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_preview)

    # ---------------------------------------------------------
    # PAGE 2: STATISTICAL SUMMARY & ACTUAL EMBEDDED CHARTS
    # ---------------------------------------------------------
    story.append(PageBreak())

    # Statistical Summary (Compact: Feature | Mean | Median | Min | Max)
    story.append(Paragraph("Statistical Summary", section_heading))
    num_stats = summary_dict.get('numeric_summary', {})
    meaningful_stats = {k: v for k, v in num_stats.items() if not is_id_column(k, df[k].dropna())}
    if not meaningful_stats:
        meaningful_stats = num_stats

    if meaningful_stats:
        stats_rows = [
            [
                Paragraph("<b>Feature</b>", table_head),
                Paragraph("<b>Mean</b>", table_head),
                Paragraph("<b>Median</b>", table_head),
                Paragraph("<b>Min</b>", table_head),
                Paragraph("<b>Max</b>", table_head),
            ]
        ]
        for col, s in list(meaningful_stats.items())[:8]:
            stats_rows.append([
                Paragraph(col[:20], table_cell),
                Paragraph(f"{s['mean']:,.2f}", table_cell),
                Paragraph(f"{s['median']:,.2f}", table_cell),
                Paragraph(f"{s['min']:,.2f}", table_cell),
                Paragraph(f"{s['max']:,.2f}", table_cell),
            ])
        t_stats = Table(stats_rows, colWidths=[180, 90, 90, 90, 90])
        t_stats.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
            ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_CARD_BG]),
            ('PADDING', (0,0), (-1,-1), 4.5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_stats)
    else:
        story.append(Paragraph("No continuous numerical attributes detected.", body_style))

    story.append(Spacer(1, 10))

    # ACTUAL EMBEDDED CHARTS (MAX 4)
    story.append(Paragraph("Visual Analysis & Patterns", section_heading))
    selected_charts = select_useful_charts(df, col_types)

    if selected_charts:
        # Group charts 2-by-2 for clean visual arrangement
        chart_pairs = [selected_charts[i:i+2] for i in range(0, len(selected_charts), 2)]
        for pair_idx, pair in enumerate(chart_pairs):
            if pair_idx > 0:
                story.append(Spacer(1, 8))

            row_cells = []
            for chart in pair:
                cell_elements = [
                    Paragraph(f"<b>{chart['title']}</b>", ParagraphStyle('ChartT', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=COLOR_DARK, spaceAfter=2)),
                    Image(chart['image_buf'], width=255, height=135),
                    Spacer(1, 2),
                    Table([[Paragraph(f"<b>Observation:</b> {chart['observation']}", chart_obs_style)]],
                          colWidths=[255],
                          style=[('BACKGROUND', (0,0), (-1,-1), COLOR_OBS_BG),
                                 ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#bfdbfe')),
                                 ('PADDING', (0,0), (-1,-1), 3)])
                ]
                row_cells.append(cell_elements)

            # If only 1 chart in this row, pad with empty
            if len(row_cells) == 1:
                row_cells.append([Paragraph("", body_style)])

            chart_table = Table([row_cells], colWidths=[265, 265])
            chart_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ]))
            story.append(chart_table)
    else:
        story.append(Paragraph("No charts could be reliably constructed from this dataset.", body_style))

    # ---------------------------------------------------------
    # PAGE 3 (OR NEXT SECTION): DATA QUALITY, AI INSIGHTS, LIMITATIONS, CONCLUSION
    # ---------------------------------------------------------
    story.append(Spacer(1, 10))

    # Compact Data Quality
    story.append(Paragraph("Data Quality Audit", section_heading))
    q_summary_text = (
        f"<b>Missing Values:</b> {missing_val:,} &nbsp;|&nbsp; "
        f"<b>Duplicate Rows:</b> {dups_val:,} &nbsp;|&nbsp; "
        f"<b>Columns Audited:</b> {cols_val}"
    )
    story.append(Paragraph(q_summary_text, bullet_style))

    # If any column has missing values, show compact table of affected columns
    missing_cols = [q for q in quality_report if q['missing'] > 0]
    if missing_cols:
        q_table_data = [[
            Paragraph("<b>Column</b>", table_head),
            Paragraph("<b>Type</b>", table_head),
            Paragraph("<b>Missing Cells</b>", table_head),
            Paragraph("<b>Missing %</b>", table_head),
            Paragraph("<b>Status</b>", table_head),
        ]]
        for q in missing_cols[:6]:
            q_table_data.append([
                Paragraph(q['column'][:20], table_cell),
                Paragraph(q['data_type'], table_cell),
                Paragraph(str(q['missing']), table_cell),
                Paragraph(f"{q['missing_pct']}%", table_cell),
                Paragraph(f"<b>{q['status']}</b>", table_cell),
            ])
        t_q = Table(q_table_data, colWidths=[180, 90, 90, 90, 90])
        t_q.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
            ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_CARD_BG]),
            ('PADDING', (0,0), (-1,-1), 3.5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_q)
    else:
        story.append(Paragraph("&bull; <b>Clean Record Quality:</b> All attributes are 100% complete with 0 missing values.", bullet_style))

    story.append(Spacer(1, 8))

    # AI Insights (Short: Maximum 5 concise bullets)
    story.append(Paragraph("Analytical & AI Insights", section_heading))
    concise_ai = format_clean_ai_insights(ai_insights_text, summary_dict, df)
    for ai_pt in concise_ai:
        story.append(Paragraph(f"&bull; {ai_pt}", bullet_style))
    story.append(Spacer(1, 8))

    # Limitations (Max 2-3 brief bullets)
    story.append(Paragraph("Limitations", section_heading))
    limitations = [
        "Findings describe the uploaded sample records and may not generalize to broader unobserved populations.",
        "Observed correlations indicate mathematical associations only and do not establish causal relationships.",
        "Domain-specific context and verification should always guide downstream operational decisions."
    ]
    for lim in limitations[:3]:
        story.append(Paragraph(f"&bull; {lim}", bullet_style))
    story.append(Spacer(1, 8))

    # Conclusion (2-3 sentences)
    story.append(Paragraph("Conclusion", section_heading))
    conclusion_text = (
        f"DataLens successfully analyzed {rows_val:,} records across {cols_val} variables in '{dataset_meta.get('filename')}'. "
        f"Data quality shows {missing_val} missing values and {dups_val} duplicate rows. "
        "The visual and statistical summary provides an objective baseline for academic exploration and reporting."
    )
    story.append(Paragraph(conclusion_text, body_style))
    story.append(Spacer(1, 10))

    # Sign-off footer
    sign_off_style = ParagraphStyle(
        'SignOff',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=COLOR_MUTED,
        alignment=1
    )
    story.append(HRFlowable(width="100%", thickness=0.8, color=COLOR_BORDER, spaceAfter=6))
    story.append(Paragraph("Generated by DataLens &bull; AI-Powered Data Analysis & Reporting", sign_off_style))

    doc.build(story)
    return output_path
