document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("upload-form");
    if (!form) return;

    const uploadUrl = form.dataset.uploadUrl;
    const statusUrlTemplate = form.dataset.statusUrl;
    const fileInput = document.getElementById("excel-file");
    const fileDrop = document.getElementById("file-drop");
    const fileLabel = document.getElementById("file-label");
    const defaultLabel = fileLabel.textContent;
    const submitBtn = document.getElementById("submit-btn");
    const statusBox = document.getElementById("job-status");
    const statusText = document.getElementById("job-status-text");
    const errorBox = document.getElementById("job-error");
    const resultBox = document.getElementById("job-result");
    const downloadLink = document.getElementById("job-download-link");

    function updateFileLabel() {
        fileLabel.textContent = fileInput.files.length ? fileInput.files[0].name : defaultLabel;
    }

    fileInput.addEventListener("change", updateFileLabel);

    ["dragover", "dragleave", "drop"].forEach(function (evt) {
        fileDrop.addEventListener(evt, function (event) {
            event.preventDefault();
            fileDrop.classList.toggle("dragover", evt === "dragover");
        });
    });

    fileDrop.addEventListener("drop", function (event) {
        const files = event.dataTransfer.files;
        if (files.length) {
            fileInput.files = files;
            updateFileLabel();
        }
    });

    function resetPanels() {
        statusBox.hidden = true;
        errorBox.hidden = true;
        resultBox.hidden = true;
    }

    function showError(message, pendingTab) {
        if (pendingTab) pendingTab.close();
        statusBox.hidden = true;
        errorBox.hidden = false;
        errorBox.textContent = message;
        submitBtn.disabled = false;
    }

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        if (!fileInput.files.length) return;

        const pendingTab = openPendingTab();

        submitBtn.disabled = true;
        resetPanels();
        statusBox.hidden = false;
        statusText.textContent = "Caricamento file...";

        const formData = new FormData();
        formData.append("excel_file", fileInput.files[0]);

        fetch(uploadUrl, { method: "POST", body: formData })
            .then(function (response) {
                return response.json().then(function (data) {
                    if (!response.ok) throw new Error(data.error || "Errore durante il caricamento.");
                    return data;
                });
            })
            .then(function (data) {
                statusText.textContent = "Generazione PDF in corso...";
                pollJob(statusUrlTemplate, data.job_id, function (job) {
                    statusBox.hidden = true;
                    resultBox.hidden = false;
                    downloadLink.href = job.download_url;
                    if (pendingTab && !pendingTab.closed) {
                        pendingTab.location.href = job.download_url;
                    } else {
                        window.open(job.download_url, "_blank");
                    }
                    submitBtn.disabled = false;
                    form.reset();
                    updateFileLabel();
                }, function (message) {
                    showError(message, pendingTab);
                });
            })
            .catch(function (err) {
                showError(err.message || "Errore durante il caricamento.", pendingTab);
            });
    });
});
