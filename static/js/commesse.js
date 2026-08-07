document.addEventListener("DOMContentLoaded", function () {
    const table = document.querySelector(".commesse-table");
    if (!table) return;

    const azioniBase = table.dataset.azioniBase;
    const checkAll = document.getElementById("check-all");
    const bulkActions = document.getElementById("bulk-actions");
    const bulkCount = document.getElementById("bulk-count");
    const btnBulkStato = document.getElementById("btn-bulk-stato");

    const statoModalOverlay = document.getElementById("stato-modal-overlay");
    const statoModalCount = document.getElementById("stato-modal-count");
    const statoModalSelect = document.getElementById("stato-modal-select");
    const statoModalApply = document.getElementById("stato-modal-apply");
    const statoModalCancel = document.getElementById("stato-modal-cancel");

    function rowChecks() {
        return table.querySelectorAll(".row-check");
    }

    function selectedIds() {
        return Array.from(rowChecks())
            .filter(function (c) { return c.checked; })
            .map(function (c) { return c.value; });
    }

    function updateBulkBar() {
        const n = selectedIds().length;
        bulkActions.hidden = n === 0;
        bulkCount.textContent = n + (n === 1 ? " selezionata" : " selezionate");
    }

    checkAll.addEventListener("change", function () {
        rowChecks().forEach(function (c) { c.checked = checkAll.checked; });
        updateBulkBar();
    });

    table.addEventListener("change", function (event) {
        if (!event.target.classList.contains("row-check")) return;
        if (!event.target.checked) checkAll.checked = false;
        updateBulkBar();
    });

    btnBulkStato.addEventListener("click", function () {
        const n = selectedIds().length;
        if (!n) return;
        statoModalCount.textContent = n + (n === 1 ? " commessa selezionata" : " commesse selezionate");
        statoModalOverlay.hidden = false;
    });

    function closeStatoModal() {
        statoModalOverlay.hidden = true;
    }

    statoModalCancel.addEventListener("click", closeStatoModal);
    statoModalOverlay.addEventListener("click", function (event) {
        if (event.target === statoModalOverlay) closeStatoModal();
    });

    statoModalApply.addEventListener("click", function () {
        const ids = selectedIds();
        const stato = statoModalSelect.value;
        if (!ids.length) return;

        fetch(azioniBase + "/stato-multiplo", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ids: ids, stato: stato }),
        })
            .then(function (response) {
                return response.json().then(function (data) {
                    if (!response.ok) throw new Error(data.error || "Errore durante l'aggiornamento.");
                    return data;
                });
            })
            .then(function (data) {
                data.aggiornate.forEach(function (item) {
                    const row = table.querySelector('tr[data-commessa-id="' + item.id + '"]');
                    if (!row) return;
                    const badge = row.querySelector(".badge");
                    badge.className = "badge badge-" + item.stato;
                    badge.dataset.stato = item.stato;
                    badge.textContent = item.stato_label;
                });
                closeStatoModal();
                rowChecks().forEach(function (c) { c.checked = false; });
                checkAll.checked = false;
                updateBulkBar();
            })
            .catch(function (err) {
                alert(err.message || "Errore durante l'aggiornamento dello stato.");
            });
    });

    table.querySelectorAll(".btn-icon-delete").forEach(function (btn) {
        btn.addEventListener("click", function () {
            const id = btn.dataset.commessaId;
            if (!confirm("Eliminare definitivamente questa commessa e tutti i suoi dati (righe, supporti e vaschette)?")) return;

            fetch(azioniBase + "/" + id + "/elimina", { method: "POST" })
                .then(function (response) {
                    return response.json().then(function (data) {
                        if (!response.ok) throw new Error(data.error || "Errore durante l'eliminazione.");
                        return data;
                    });
                })
                .then(function () {
                    const row = btn.closest("tr");
                    if (row) row.remove();
                })
                .catch(function (err) {
                    alert(err.message || "Errore durante l'eliminazione.");
                });
        });
    });
});
