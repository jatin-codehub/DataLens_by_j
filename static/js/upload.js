// upload.js - Handles file selection, drag & drop, client validation, and submission

document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const fileDetails = document.getElementById('fileDetails');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const removeFileBtn = document.getElementById('removeFileBtn');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const uploadForm = document.getElementById('uploadForm');
    const loadingState = document.getElementById('loadingState');
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');

    const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
    const ALLOWED_EXTS = ['.csv', '.xlsx', '.xls'];

    let selectedFile = null;

    function showError(msg) {
        errorMessage.textContent = msg;
        errorAlert.classList.remove('d-none');
    }

    function hideError() {
        errorAlert.classList.add('d-none');
        errorMessage.textContent = '';
    }

    function formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function handleFile(file) {
        hideError();
        if (!file) return;

        const name = file.name.toLowerCase();
        const isValidExt = ALLOWED_EXTS.some(ext => name.endsWith(ext));

        if (!isValidExt) {
            showError("Please upload a valid CSV or Excel file (.csv, .xlsx, .xls).");
            resetSelection();
            return;
        }

        if (file.size > MAX_FILE_SIZE) {
            showError(`File is too large (${formatBytes(file.size)}). Maximum allowed file size is 10 MB.`);
            resetSelection();
            return;
        }

        if (file.size === 0) {
            showError("The selected file is empty. Please choose a dataset with rows.");
            resetSelection();
            return;
        }

        selectedFile = file;
        fileName.textContent = file.name;
        fileSize.textContent = formatBytes(file.size);

        fileDetails.classList.remove('d-none');
        dropZone.classList.add('d-none');
        analyzeBtn.disabled = false;
    }

    function resetSelection() {
        selectedFile = null;
        fileInput.value = '';
        fileDetails.classList.add('d-none');
        dropZone.classList.remove('d-none');
        analyzeBtn.disabled = true;
    }

    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    // Remove file button
    removeFileBtn.addEventListener('click', resetSelection);

    // Drag & Drop listeners
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('dragover');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        if (dt.files && dt.files.length > 0) {
            handleFile(dt.files[0]);
        }
    });

    // Form submission
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!selectedFile) return;

        hideError();
        uploadForm.classList.add('d-none');
        loadingState.classList.remove('d-none');

        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.success) {
                // Redirect directly to dashboard
                window.location.href = `/dashboard/${data.dataset_id}`;
            } else {
                uploadForm.classList.remove('d-none');
                loadingState.classList.add('d-none');
                showError(data.error || "Failed to process the dataset. Please check the file.");
            }
        } catch (err) {
            uploadForm.classList.remove('d-none');
            loadingState.classList.add('d-none');
            showError("Network connection error while uploading. Please ensure the server is active.");
        }
    });
});
