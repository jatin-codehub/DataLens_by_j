// dashboard.js - Dynamic analytics loader, Plotly renderer, and Q&A engine

document.addEventListener('DOMContentLoaded', () => {
    const datasetId = document.body.dataset.datasetId;
    if (!datasetId) return;

    // Load components in parallel
    loadPreview();
    loadStatistics();
    loadQuality();
    loadCharts();
    loadAiInsights();

    setupAskData();
    setupPdfGenerator();
    setupClearSession();
});

// Helper: Format Markdown to clean, readable HTML
function formatMarkdown(text) {
    if (!text) return '';
    let html = text
        .replace(/^### (.*$)/gim, '<h6 class="fw-bold text-dark mt-2 mb-1">$1</h6>')
        .replace(/^## (.*$)/gim, '<h6 class="fw-bold text-dark mt-2 mb-1">$1</h6>')
        .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/gim, '<em>$1</em>')
        .replace(/`([^`]+)`/gim, '<code>$1</code>')
        .replace(/^\- (.*$)/gim, '<li class="mb-1">$1</li>')
        .replace(/^\* (.*$)/gim, '<li class="mb-1">$1</li>');

    // Wrap <li> tags into <ul>
    html = html.replace(/(<li class="mb-1">[\s\S]*?<\/li>)/gm, '<ul class="ps-3 mb-2">$1</ul>');
    html = html.replace(/<\/ul>\s*<ul class="ps-3 mb-2">/g, '');
    html = html.replace(/\n\n+/g, '<p class="mb-2">');
    return html;
}

// 1. Load Dataset Preview
async function loadPreview() {
    try {
        const res = await fetch(`/api/dataset/${document.body.dataset.datasetId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (!data.success) throw new Error(data.error);

        const preview = data.preview;
        document.getElementById('previewCountBadge').textContent = `Showing ${preview.total_previewed} of ${preview.total_rows.toLocaleString()} records`;

        // Headings
        const thead = document.getElementById('previewTableHead');
        thead.innerHTML = preview.columns.map(c => `
            <th>
                <div>${c.name}</div>
                <span class="badge-clean badge-neutral" style="font-size: 0.7rem; font-weight: normal;">${c.dtype}</span>
            </th>
        `).join('');

        // Rows
        const tbody = document.getElementById('previewTableBody');
        tbody.innerHTML = preview.rows.map(row => `
            <tr>
                ${preview.columns.map(c => {
                    const val = row[c.name];
                    return `<td>${val !== null && val !== undefined ? val : '<span class="text-muted">null</span>'}</td>`;
                }).join('')}
            </tr>
        `).join('');

    } catch (err) {
        document.getElementById('previewTableBody').innerHTML = `
            <tr><td colspan="10" class="text-center py-4 text-secondary">Unable to load preview: ${err.message}</td></tr>
        `;
    }
}

// 2. Load Statistical Summary
async function loadStatistics() {
    try {
        const res = await fetch(`/api/dataset/${document.body.dataset.datasetId}/statistics`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (!data.success) throw new Error(data.error);

        const stats = data.statistics;
        const tbody = document.getElementById('statsTableBody');

        const keys = Object.keys(stats);
        if (keys.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-secondary">No numerical features found.</td></tr>`;
            return;
        }

        tbody.innerHTML = keys.map(col => {
            const s = stats[col];
            return `
                <tr>
                    <td class="fw-semibold text-dark">${col}</td>
                    <td class="text-end">${s.count.toLocaleString()}</td>
                    <td class="text-end fw-semibold" style="color: var(--accent-primary);">${s.mean.toLocaleString()}</td>
                    <td class="text-end">${s.median.toLocaleString()}</td>
                    <td class="text-end">${s.min.toLocaleString()}</td>
                    <td class="text-end">${s.max.toLocaleString()}</td>
                    <td class="text-end text-secondary">${s.std.toLocaleString()}</td>
                </tr>
            `;
        }).join('');

    } catch (err) {
        document.getElementById('statsTableBody').innerHTML = `
            <tr><td colspan="7" class="text-center py-4 text-secondary">Unable to load statistics: ${err.message}</td></tr>
        `;
    }
}

// 3. Load Data Quality Audit
async function loadQuality() {
    try {
        const res = await fetch(`/api/dataset/${document.body.dataset.datasetId}/quality`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (!data.success) throw new Error(data.error);

        const quality = data.quality;
        const cleaning = data.cleaning;

        // Cleaning notice
        const notice = document.getElementById('cleaningNotice');
        const noticeText = document.getElementById('cleaningNoticeText');
        if (cleaning.duplicate_rows > 0 || cleaning.empty_columns.length > 0) {
            notice.classList.remove('d-none');
            let msgs = [];
            if (cleaning.duplicate_rows > 0) {
                msgs.push(`Found <strong>${cleaning.duplicate_rows} duplicate rows</strong> (${cleaning.clean_rows_estimate.toLocaleString()} clean rows remaining if deduplicated).`);
            }
            if (cleaning.empty_columns.length > 0) {
                msgs.push(`Completely unpopulated columns: <code>${cleaning.empty_columns.join(', ')}</code>.`);
            }
            noticeText.innerHTML = msgs.join(' &bull; ');
        }

        // Quality table
        const tbody = document.getElementById('qualityTableBody');
        tbody.innerHTML = quality.map(q => {
            let badgeClass = 'badge-good';
            if (q.status === 'Warning') badgeClass = 'badge-warning';
            if (q.status === 'Needs Attention') badgeClass = 'badge-danger';

            return `
                <tr>
                    <td class="fw-semibold text-dark">${q.column}</td>
                    <td><code>${q.data_type}</code></td>
                    <td class="text-end">${q.missing}</td>
                    <td class="text-end font-monospace">${q.missing_pct}%</td>
                    <td class="text-end">${q.unique}</td>
                    <td class="text-center">
                        <span class="badge-clean ${badgeClass}">${q.status}</span>
                    </td>
                </tr>
            `;
        }).join('');

    } catch (err) {
        document.getElementById('qualityTableBody').innerHTML = `
            <tr><td colspan="6" class="text-center py-4 text-secondary">Unable to audit data quality: ${err.message}</td></tr>
        `;
    }
}

// 4. Load & Render Visualizations (Plotly)
async function loadCharts() {
    const container = document.getElementById('chartsContainer');
    try {
        const res = await fetch(`/api/dataset/${document.body.dataset.datasetId}/charts`);
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.error || `Server returned ${res.status}`);
        }

        const data = await res.json();
        if (!data.success) throw new Error(data.error);

        const charts = data.charts;
        if (!charts || charts.length === 0) {
            container.innerHTML = `<div class="col-12 text-center py-4 text-secondary">No suitable visual charts could be automatically constructed for this dataset.</div>`;
            return;
        }

        container.innerHTML = '';

        charts.forEach((chart, idx) => {
            const colSize = (chart.type === 'heatmap' || charts.length === 1) ? 'col-12' : 'col-lg-6';
            const cardHtml = `
                <div class="${colSize}">
                    <div class="chart-box">
                        <div class="chart-header">
                            <h3 class="chart-title">${chart.title}</h3>
                            <span class="badge-clean badge-neutral text-uppercase" style="font-size: 0.7rem;">${chart.type}</span>
                        </div>
                        <div id="plotlyChart_${idx}" style="min-height: 310px; width: 100%;"></div>
                    </div>
                </div>
            `;
            container.insertAdjacentHTML('beforeend', cardHtml);

            // Render with clean Plotly config
            Plotly.newPlot(`plotlyChart_${idx}`, chart.spec.data, chart.spec.layout, {
                responsive: true,
                displayModeBar: true,
                displaylogo: false,
                modeBarButtonsToRemove: ['lasso2d', 'select2d']
            });
        });

    } catch (err) {
        container.innerHTML = `
            <div class="col-12 text-center py-4" style="color: var(--error); font-size: 0.86rem;">
                Unable to render visualizations: ${err.message}
            </div>
        `;
    }
}

// 5. Load Key Findings
async function loadAiInsights() {
    const container = document.getElementById('aiInsightsText');
    const loading = document.getElementById('aiLoadingIndicator');
    const modeIndicator = document.getElementById('aiModeIndicator');

    container.classList.add('d-none');
    loading.classList.remove('d-none');

    try {
        const res = await fetch(`/api/dataset/${document.body.dataset.datasetId}/insights`, {
            method: 'POST'
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        loading.classList.add('d-none');
        container.classList.remove('d-none');

        if (data.success) {
            container.innerHTML = formatMarkdown(data.insights);
            if (data.mode === 'gemini') {
                modeIndicator.textContent = "Synthesized via Gemini 1.5 Flash";
            } else {
                modeIndicator.textContent = "Calculated from dataset statistics";
            }
        } else {
            container.innerHTML = `<div class="text-secondary small">${data.message || 'Key findings temporarily unavailable.'}</div>`;
        }
    } catch (err) {
        loading.classList.add('d-none');
        container.classList.remove('d-none');
        container.innerHTML = `<div class="text-secondary small">Unable to fetch key findings: ${err.message}</div>`;
    }
}

// Refresh findings listener
document.getElementById('regenerateAiBtn').addEventListener('click', () => {
    loadAiInsights();
});

// 6. Setup "Ask Your Data" Q&A
function setupAskData() {
    const form = document.getElementById('askForm');
    const input = document.getElementById('userQuestion');
    const btn = document.getElementById('askBtn');
    const answerPlaceholder = document.getElementById('answerPlaceholder');
    const answerContent = document.getElementById('answerContent');
    const answerText = document.getElementById('answerText');
    const answerMethod = document.getElementById('answerMethod');

    window.askPreset = function(q) {
        input.value = q;
        submitQuestion(q);
    };

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const q = input.value.trim();
        if (q) submitQuestion(q);
    });

    async function submitQuestion(question) {
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span>`;
        answerPlaceholder.classList.add('d-none');
        answerContent.classList.remove('d-none');
        answerText.innerHTML = `<span class="text-secondary fst-italic">Evaluating query with Pandas...</span>`;
        answerMethod.textContent = '';

        try {
            const res = await fetch(`/api/dataset/${document.body.dataset.datasetId}/ask`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: question })
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            if (data.success) {
                answerText.innerHTML = formatMarkdown(data.answer);
                answerMethod.textContent = data.method || '';
            } else {
                answerText.innerHTML = `<span style="color: var(--error);">${data.error || 'Failed to answer query.'}</span>`;
            }
        } catch (err) {
            answerText.innerHTML = `<span style="color: var(--error);">Query error: ${err.message}</span>`;
        } finally {
            btn.disabled = false;
            btn.textContent = 'Query';
        }
    }
}

// 7. Setup PDF Report Generator Modal
function setupPdfGenerator() {
    const btn = document.getElementById('generatePdfBtn');
    const modalElement = document.getElementById('pdfModal');
    const modal = new bootstrap.Modal(modalElement);
    const loadingState = document.getElementById('pdfLoadingState');
    const successState = document.getElementById('pdfSuccessState');
    const downloadLink = document.getElementById('downloadPdfLink');

    btn.addEventListener('click', async () => {
        loadingState.classList.remove('d-none');
        successState.classList.add('d-none');
        modal.show();

        try {
            const res = await fetch(`/api/dataset/${document.body.dataset.datasetId}/report`, {
                method: 'POST'
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            if (data.success) {
                const repId = data.session_id || data.report_id;
                downloadLink.href = `/api/report/${repId}/download`;
                loadingState.classList.add('d-none');
                successState.classList.remove('d-none');
            } else {
                modal.hide();
                alert('Report generation failed: ' + (data.error || 'Unknown error'));
            }
        } catch (err) {
            modal.hide();
            alert('Connection error generating PDF: ' + err.message);
        }
    });
}

// 8. Setup Clear Session Handler
function setupClearSession() {
    const confirmBtn = document.getElementById('confirmClearSessionBtn');
    if (!confirmBtn) return;

    confirmBtn.addEventListener('click', async () => {
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Clearing...';

        const sid = document.body.dataset.datasetId;
        try {
            await fetch(`/api/session/${sid}/clear`, { method: 'POST' });
        } catch (e) {
            // Ignore error if cleanup network fails
        } finally {
            sessionStorage.clear();
            localStorage.removeItem('datalens_session');
            window.location.href = '/?cleared=true';
        }
    });
}

