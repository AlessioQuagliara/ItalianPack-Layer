document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("cartello-form");
    if (!form) return;

    const generaUrl = form.dataset.generaUrl;
    const statusUrlTemplate = form.dataset.statusUrl;
    const submitBtn = document.getElementById("submit-btn");
    const statusBox = document.getElementById("job-status");
    const statusText = document.getElementById("job-status-text");
    const errorBox = document.getElementById("job-error");
    const resultBox = document.getElementById("job-result");
    const downloadLink = document.getElementById("job-download-link");

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

        const pendingTab = openPendingTab();

        submitBtn.disabled = true;
        resetPanels();
        statusBox.hidden = false;
        statusText.textContent = "Generazione PDF in corso...";

        const formData = new FormData(form);

        fetch(generaUrl, { method: "POST", body: formData })
            .then(function (response) {
                return response.json().then(function (data) {
                    if (!response.ok) throw new Error(data.error || "Errore durante la generazione.");
                    return data;
                });
            })
            .then(function (data) {
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
                }, function (message) {
                    showError(message, pendingTab);
                });
            })
            .catch(function (err) {
                showError(err.message || "Errore durante la generazione.", pendingTab);
            });
    });
});
