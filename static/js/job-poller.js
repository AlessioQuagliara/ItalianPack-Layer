function openPendingTab() {
    const tab = window.open("", "_blank");
    if (tab) {
        tab.document.title = "Generazione PDF...";
        tab.document.write("<p style='font-family:sans-serif;padding:2rem;'>Generazione PDF in corso...</p>");
    }
    return tab;
}

function pollJob(statusUrlTemplate, jobId, onDone, onError) {
    const statusUrl = statusUrlTemplate.replace("JOBID", jobId);

    const timer = setInterval(function () {
        fetch(statusUrl)
            .then(function (response) { return response.json(); })
            .then(function (job) {
                if (job.status === "done") {
                    clearInterval(timer);
                    onDone(job);
                } else if (job.status === "error") {
                    clearInterval(timer);
                    onError(job.error || "Errore sconosciuto durante la generazione del PDF.");
                }
            })
            .catch(function () {
                clearInterval(timer);
                onError("Errore di comunicazione con il server.");
            });
    }, 1200);
}
