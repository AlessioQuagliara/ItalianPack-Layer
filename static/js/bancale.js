document.addEventListener("DOMContentLoaded", function () {
    const wrap = document.querySelector(".bancale-wrap");
    if (!wrap) return;

    const contenitoreId = Number(wrap.dataset.contenitoreId);
    const vaschetteUrl = wrap.dataset.vaschetteUrl;
    const vaschettaItemBase = wrap.dataset.vaschettaItemBase;
    const contenitoriUrl = wrap.dataset.contenitoriUrl;
    const eliminaSupportoBase = wrap.dataset.eliminaSupportoBase;
    const stampaEtichetteUrl = wrap.dataset.stampaEtichetteUrl;
    const stampaCartelloUrl = wrap.dataset.stampaCartelloUrl;
    const jobStatusBase = wrap.dataset.jobStatusBase;
    const mappaBase = wrap.dataset.mappaBase;
    const vistaLettura = wrap.dataset.vistaLettura === "true";

    const PALLET_W = Number(wrap.dataset.palletW);
    const PALLET_H = Number(wrap.dataset.palletH);
    const GRID = 10; // 1 cm, scala 1:10
    const SNAP_MAGNETICO = 20; // px di "calamita" verso i bordi delle vaschette vicine

    const pallet = document.getElementById("bancale-pallet");
    const palletFrame = document.querySelector(".bancale-pallet-frame");
    const stage = document.querySelector(".bancale-stage");
    const tooltip = document.getElementById("bancale-tooltip");
    const searchInput = document.getElementById("bancale-search-input");
    const searchToast = document.getElementById("search-toast");

    const DIMS = { slim: { w: 600, h: 130 }, medium: { w: 600, h: 270 }, big: { w: 600, h: 400 } };

    function effectiveDims(tipo, ruotata) {
        const base = DIMS[tipo];
        return ruotata ? { w: base.h, h: base.w } : { w: base.w, h: base.h };
    }

    const righeData = JSON.parse(document.getElementById("bancale-righe-data").textContent);
    const vaschetteData = JSON.parse(document.getElementById("bancale-vaschette-data").textContent);
    const contenitoriData = JSON.parse(document.getElementById("bancale-contenitori-data").textContent);
    const ricercaGlobale = JSON.parse(document.getElementById("bancale-ricerca-globale-data").textContent);

    const nomeContenitoreMap = new Map();
    contenitoriData.forEach(function (c) { nomeContenitoreMap.set(c.id, c.nome); });

    const gruppiMap = new Map();
    righeData.forEach(function (r) {
        if (!r.gruppo) return;
        if (!gruppiMap.has(r.gruppo)) {
            gruppiMap.set(r.gruppo, { descrizione: r.descrizione_gruppo || "", codici: [] });
        }
        if (r.codice) gruppiMap.get(r.gruppo).codici.push(r.codice);
    });

    const state = { vaschette: new Map() };
    vaschetteData.forEach(function (v) { state.vaschette.set(v.id, v); });

    function itemUrl(id) {
        return vaschettaItemBase + "/" + id;
    }

    function snap(value) {
        return Math.round(value / GRID) * GRID;
    }

    // Overlap AABB: due rettangoli collidono SOLO se si sovrappongono sia in X che in Y.
    function rectsOverlap(a, b) {
        const overlapX = a.x < b.x + b.w && a.x + a.w > b.x;
        const overlapY = a.y < b.y + b.h && a.y + a.h > b.y;
        return overlapX && overlapY;
    }

    function clampRect(rect) {
        rect.x = Math.min(Math.max(rect.x, 0), PALLET_W - rect.w);
        rect.y = Math.min(Math.max(rect.y, 0), PALLET_H - rect.h);
        return rect;
    }

    function hasCollision(rect, excludeId) {
        for (const v of state.vaschette.values()) {
            if (v.id === excludeId) continue;
            if (rectsOverlap(rect, v)) return true;
        }
        return false;
    }

    function rectDentroLimiti(rect) {
        return rect.x >= 0 && rect.y >= 0 && rect.x + rect.w <= PALLET_W && rect.y + rect.h <= PALLET_H;
    }

    function rectValida(rect, excludeId) {
        return rectDentroLimiti(rect) && !hasCollision(rect, excludeId);
    }

    // Calamita verso i bordi delle vaschette vicine: se il rettangolo trascinato
    // è a pochi px dal combaciare esattamente con un vicino (bordo contro bordo,
    // con le fasce che si sovrappongono sull'asse perpendicolare), lo aggancia
    // esattamente a contatto.
    function snapToNeighbors(rect, excludeId) {
        let bestX = null, bestXDist = SNAP_MAGNETICO;
        let bestY = null, bestYDist = SNAP_MAGNETICO;

        for (const v of state.vaschette.values()) {
            if (v.id === excludeId) continue;

            const yOverlap = rect.y < v.y + v.h && rect.y + rect.h > v.y;
            if (yOverlap) {
                const distRight = Math.abs(rect.x - (v.x + v.w));
                if (distRight < bestXDist) { bestXDist = distRight; bestX = v.x + v.w; }
                const distLeft = Math.abs((rect.x + rect.w) - v.x);
                if (distLeft < bestXDist) { bestXDist = distLeft; bestX = v.x - rect.w; }
            }

            const xOverlap = rect.x < v.x + v.w && rect.x + rect.w > v.x;
            if (xOverlap) {
                const distBottom = Math.abs(rect.y - (v.y + v.h));
                if (distBottom < bestYDist) { bestYDist = distBottom; bestY = v.y + v.h; }
                const distTop = Math.abs((rect.y + rect.h) - v.y);
                if (distTop < bestYDist) { bestYDist = distTop; bestY = v.y - rect.h; }
            }
        }

        if (bestX !== null) rect.x = bestX;
        if (bestY !== null) rect.y = bestY;
        return rect;
    }

    function getScale() {
        const rect = pallet.getBoundingClientRect();
        return rect.width / PALLET_W;
    }

    function applyResponsiveScale() {
        const available = stage.clientWidth - 40;
        const scale = Math.min(1, available / PALLET_W);
        pallet.style.transform = "scale(" + scale + ")";
        palletFrame.style.width = (PALLET_W * scale) + "px";
        palletFrame.style.height = (PALLET_H * scale) + "px";
    }

    applyResponsiveScale();
    window.addEventListener("resize", applyResponsiveScale);

    function elementFor(id) {
        return pallet.querySelector('.vaschetta[data-id="' + id + '"]');
    }

    function renderVaschetta(v) {
        let el = elementFor(v.id);
        if (!el) {
            el = document.createElement("div");
            el.className = "vaschetta tipo-" + v.tipo;
            el.dataset.id = v.id;
            const label = document.createElement("span");
            label.className = "vaschetta-label";
            el.appendChild(label);
            pallet.appendChild(el);
            wireVaschettaEvents(el);
        }
        el.style.left = v.x + "px";
        el.style.top = v.y + "px";
        el.style.width = v.w + "px";
        el.style.height = v.h + "px";
        el.classList.toggle("senza-gruppo", !v.gruppo);
        el.classList.toggle("ruotata", !!v.ruotata);
        el.querySelector(".vaschetta-label").textContent = v.gruppo || "";
        return el;
    }

    function renderAll() {
        pallet.querySelectorAll(".vaschetta").forEach(function (el) { el.remove(); });
        state.vaschette.forEach(renderVaschetta);
    }

    renderAll();

    // ---- Drag: vaschette già piazzate ----
    let clickTimeout = null;

    function wireVaschettaEvents(el) {
        // In modalità vista lettura (tablet in magazzino) drag, click-per-modale
        // e doppio-click-per-ruotare sono disattivati: restano attivi solo
        // hover/tooltip, ricerca ed evidenziazione, utili per il prelievo.
        if (!vistaLettura) {
            el.addEventListener("pointerdown", function (event) {
                event.preventDefault();
                startDragExisting(el, event);
            });
            el.addEventListener("dblclick", function (event) {
                event.preventDefault();
                if (clickTimeout) {
                    clearTimeout(clickTimeout);
                    clickTimeout = null;
                }
                const v = state.vaschette.get(Number(el.dataset.id));
                if (v) ruotaVaschetta(v);
            });
        }
        el.addEventListener("pointerenter", function (event) {
            const v = state.vaschette.get(Number(el.dataset.id));
            if (v && v.gruppo) showTooltip(v, event);
        });
        el.addEventListener("pointermove", function (event) {
            if (!tooltip.hidden) positionTooltip(event);
        });
        el.addEventListener("pointerleave", hideTooltip);
    }

    function startDragExisting(el, downEvent) {
        const id = Number(el.dataset.id);
        const v = state.vaschette.get(id);
        const startX = downEvent.clientX;
        const startY = downEvent.clientY;
        const originX = v.x;
        const originY = v.y;
        const originRuotata = !!v.ruotata;
        let moved = false;
        let candidate = null;
        let collide = false;
        let ruotataCorrente = originRuotata;
        let lastEvent = downEvent;

        hideTooltip();
        el.classList.add("dragging");
        el.setPointerCapture(downEvent.pointerId);

        // Lo scale (per via del transform:scale() responsive) viene ricalcolato
        // ad ogni ricalcolo invece di essere fissato una volta all'inizio del
        // drag: se cambiasse a metà trascinamento (resize finestra, rotazione
        // del tablet) le coordinate restano sempre corrette.
        function ricalcola(event) {
            const scale = getScale();
            const dims = effectiveDims(v.tipo, ruotataCorrente);
            const dx = (event.clientX - startX) / scale;
            const dy = (event.clientY - startY) / scale;
            if (Math.abs(dx) > 3 || Math.abs(dy) > 3) moved = true;

            candidate = clampRect({ x: snap(originX + dx), y: snap(originY + dy), w: dims.w, h: dims.h });
            candidate = clampRect(snapToNeighbors(candidate, id));
            collide = hasCollision(candidate, id);
            el.classList.toggle("collide", collide);
            el.classList.toggle("ruotata", ruotataCorrente);
            el.style.left = candidate.x + "px";
            el.style.top = candidate.y + "px";
            el.style.width = dims.w + "px";
            el.style.height = dims.h + "px";
        }

        function onMove(event) {
            lastEvent = event;
            ricalcola(event);
        }

        function onKeyDown(event) {
            if (event.key.toLowerCase() !== "r") return;
            event.preventDefault();
            ruotataCorrente = !ruotataCorrente;
            ricalcola(lastEvent);
        }

        function onUp(event) {
            el.releasePointerCapture(event.pointerId);
            el.classList.remove("dragging", "collide");
            document.removeEventListener("pointermove", onMove);
            document.removeEventListener("pointerup", onUp);
            document.removeEventListener("keydown", onKeyDown);

            // Ricalcola un'ultima volta sulle coordinate ESATTE del rilascio:
            // il browser può accorpare/saltare eventi pointermove sui movimenti
            // rapidi, quindi l'ultimo valore noto da "onMove" potrebbe essere
            // leggermente disallineato dal punto di rilascio effettivo.
            ricalcola(event);

            if (!moved && ruotataCorrente === originRuotata) {
                renderVaschetta(v);
                if (clickTimeout) clearTimeout(clickTimeout);
                clickTimeout = setTimeout(function () {
                    clickTimeout = null;
                    openModal(v);
                }, 220);
                return;
            }

            if (!candidate || collide) {
                renderVaschetta(v);
                return;
            }

            savePosizione(v, candidate.x, candidate.y, ruotataCorrente);
        }

        document.addEventListener("pointermove", onMove);
        document.addEventListener("pointerup", onUp);
        document.addEventListener("keydown", onKeyDown);
    }

    // ---- Drag: nuova vaschetta dalla palette (disattivata in vista lettura) ----
    if (!vistaLettura) {
        document.querySelectorAll(".palette-item").forEach(function (item) {
            item.addEventListener("pointerdown", function (downEvent) {
                downEvent.preventDefault();
                startDragNew(item.dataset.tipo, downEvent);
            });
        });
    }

    function startDragNew(tipo, downEvent) {
        let ruotata = false;
        let dims = effectiveDims(tipo, ruotata);

        const ghost = document.createElement("div");
        ghost.className = "vaschetta tipo-" + tipo + " dragging";
        ghost.style.width = dims.w + "px";
        ghost.style.height = dims.h + "px";
        ghost.style.position = "fixed";
        ghost.style.left = downEvent.clientX + "px";
        ghost.style.top = downEvent.clientY + "px";
        ghost.style.zIndex = "999";
        ghost.style.pointerEvents = "none";
        document.body.appendChild(ghost);

        let lastCandidate = null;
        let lastEvent = downEvent;

        function ricalcolaGhost() {
            dims = effectiveDims(tipo, ruotata);
            ghost.style.width = dims.w + "px";
            ghost.style.height = dims.h + "px";
            ghost.classList.toggle("ruotata", ruotata);

            const rect = pallet.getBoundingClientRect();
            const scale = getScale();
            const inside =
                lastEvent.clientX >= rect.left && lastEvent.clientX <= rect.right &&
                lastEvent.clientY >= rect.top && lastEvent.clientY <= rect.bottom;

            if (inside) {
                const localX = (lastEvent.clientX - rect.left) / scale - dims.w / 2;
                const localY = (lastEvent.clientY - rect.top) / scale - dims.h / 2;
                let candidate = clampRect({ x: snap(localX), y: snap(localY), w: dims.w, h: dims.h });
                candidate = clampRect(snapToNeighbors(candidate, null));
                const collide = hasCollision(candidate, null);
                ghost.classList.toggle("collide", collide);
                ghost.style.left = (rect.left + candidate.x * scale) + "px";
                ghost.style.top = (rect.top + candidate.y * scale) + "px";
                lastCandidate = collide ? null : candidate;
            } else {
                ghost.style.left = lastEvent.clientX + "px";
                ghost.style.top = lastEvent.clientY + "px";
                lastCandidate = null;
                ghost.classList.remove("collide");
            }
        }

        function onMove(event) {
            lastEvent = event;
            ricalcolaGhost();
        }

        function onKeyDown(event) {
            if (event.key.toLowerCase() !== "r") return;
            event.preventDefault();
            ruotata = !ruotata;
            ricalcolaGhost();
        }

        function onUp(event) {
            document.removeEventListener("pointermove", onMove);
            document.removeEventListener("pointerup", onUp);
            document.removeEventListener("keydown", onKeyDown);

            // Come per il drag di una vaschetta esistente: ricalcola sulla
            // posizione esatta di rilascio, non su quella (potenzialmente
            // leggermente stale) dell'ultimo pointermove.
            lastEvent = event;
            ricalcolaGhost();

            ghost.remove();
            if (lastCandidate) {
                creaVaschetta(tipo, lastCandidate.x, lastCandidate.y, ruotata);
            }
        }

        document.addEventListener("pointermove", onMove);
        document.addEventListener("pointerup", onUp);
        document.addEventListener("keydown", onKeyDown);
    }

    // ---- AJAX vaschette ----
    function creaVaschetta(tipo, x, y, ruotata) {
        fetch(vaschetteUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tipo: tipo, x: x, y: y, ruotata: !!ruotata }),
        })
            .then(function (response) {
                return response.json().then(function (data) {
                    if (!response.ok) throw new Error(data.error || "Errore durante la creazione.");
                    return data;
                });
            })
            .then(function (v) {
                state.vaschette.set(v.id, v);
                renderVaschetta(v);
            })
            .catch(function (err) {
                alert(err.message || "Errore durante la creazione della vaschetta.");
            });
    }

    function savePosizione(v, x, y, ruotata) {
        fetch(itemUrl(v.id), {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ x: x, y: y, ruotata: !!ruotata }),
        })
            .then(function (response) {
                return response.json().then(function (data) {
                    if (!response.ok) throw new Error(data.error || "Errore durante il salvataggio.");
                    return data;
                });
            })
            .then(function (data) {
                state.vaschette.set(data.id, data);
                renderVaschetta(data);
            })
            .catch(function (err) {
                alert(err.message || "Errore durante il salvataggio della posizione.");
                renderVaschetta(v); // v non è mai stata modificata prima della risposta: ripristina lo stato noto
            });
    }

    function ruotaVaschetta(v) {
        const nuovaRuotata = !v.ruotata;
        const dims = effectiveDims(v.tipo, nuovaRuotata);
        const rect = { x: v.x, y: v.y, w: dims.w, h: dims.h };

        if (!rectValida(rect, v.id)) {
            alert("Non c'è spazio per ruotare questa vaschetta qui: spostala prima di ruotarla, oppure libera lo spazio intorno.");
            return;
        }

        fetch(itemUrl(v.id), {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ruotata: nuovaRuotata }),
        })
            .then(function (response) {
                return response.json().then(function (data) {
                    if (!response.ok) throw new Error(data.error || "Errore durante la rotazione.");
                    return data;
                });
            })
            .then(function (data) {
                state.vaschette.set(data.id, data);
                renderVaschetta(data);
                if (modalVaschettaId === data.id) {
                    modalTipo.textContent = "Vaschetta " + data.tipo.toUpperCase() + (data.ruotata ? " (ruotata 90°)" : "");
                }
            })
            .catch(function (err) {
                alert(err.message || "Errore durante la rotazione.");
            });
    }

    // ---- Modale assegnazione gruppo (input per pistola barcode) ----
    const modalOverlay = document.getElementById("bancale-modal-overlay");
    const modalInput = document.getElementById("bancale-modal-input");
    const modalError = document.getElementById("bancale-modal-error");
    const modalTipo = document.getElementById("bancale-modal-tipo");
    const modalSave = document.getElementById("bancale-modal-save");
    const modalCancel = document.getElementById("bancale-modal-cancel");
    const modalDelete = document.getElementById("bancale-modal-delete");
    const modalRotate = document.getElementById("bancale-modal-rotate");
    const modalGruppiList = document.getElementById("bancale-modal-gruppi-list");
    let modalVaschettaId = null;

    gruppiMap.forEach(function (info, gruppo) {
        const li = document.createElement("li");
        li.textContent = gruppo + " — " + info.descrizione + " (" + info.codici.length + " art.)";
        modalGruppiList.appendChild(li);
    });

    function resolveGruppo(rawValue) {
        const value = rawValue.trim();
        if (!value) return { ok: true, gruppo: null };

        const lower = value.toLowerCase();
        for (const gruppo of gruppiMap.keys()) {
            if (gruppo.toLowerCase() === lower) return { ok: true, gruppo: gruppo };
        }

        const riga = righeData.find(function (r) {
            return r.codice && r.gruppo && r.codice.toLowerCase() === lower;
        });
        if (riga) return { ok: true, gruppo: riga.gruppo };

        return { ok: false };
    }

    function openModal(v) {
        modalVaschettaId = v.id;
        modalTipo.textContent = "Vaschetta " + v.tipo.toUpperCase() + (v.ruotata ? " (ruotata 90°)" : "");
        modalInput.value = v.gruppo || "";
        modalError.hidden = true;
        modalOverlay.hidden = false;
        requestAnimationFrame(function () {
            modalInput.focus();
            modalInput.select();
        });
    }

    function closeModal() {
        modalOverlay.hidden = true;
        modalVaschettaId = null;
    }

    modalCancel.addEventListener("click", closeModal);
    modalOverlay.addEventListener("click", function (event) {
        if (event.target === modalOverlay) closeModal();
    });
    document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape") return;
        if (!modalOverlay.hidden) closeModal();
        if (!supportoModalOverlay.hidden) closeSupportoModal();
        if (!cartelloModalOverlay.hidden) closeCartelloModal();
    });

    function salvaAssegnazione() {
        if (modalVaschettaId === null) return;

        const result = resolveGruppo(modalInput.value);
        if (!result.ok) {
            modalError.hidden = false;
            modalError.textContent = "Codice non riconosciuto in questa commessa.";
            modalInput.select();
            return;
        }
        modalError.hidden = true;

        fetch(itemUrl(modalVaschettaId), {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ gruppo: result.gruppo }),
        })
            .then(function (response) {
                return response.json().then(function (data) {
                    if (!response.ok) throw new Error(data.error || "Errore durante l'assegnazione.");
                    return data;
                });
            })
            .then(function (data) {
                state.vaschette.set(data.id, data);
                renderVaschetta(data);
                closeModal();
            })
            .catch(function (err) {
                modalError.hidden = false;
                modalError.textContent = err.message || "Errore durante l'assegnazione del gruppo.";
            });
    }

    modalSave.addEventListener("click", salvaAssegnazione);
    modalInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            salvaAssegnazione();
        }
    });

    modalRotate.addEventListener("click", function () {
        if (modalVaschettaId === null) return;
        const v = state.vaschette.get(modalVaschettaId);
        if (v) ruotaVaschetta(v);
    });

    modalDelete.addEventListener("click", function () {
        if (modalVaschettaId === null) return;
        if (!confirm("Rimuovere questa vaschetta dal supporto?")) return;

        fetch(itemUrl(modalVaschettaId), { method: "DELETE" })
            .then(function (response) {
                return response.json().then(function (data) {
                    if (!response.ok) throw new Error(data.error || "Errore durante la rimozione.");
                    return data;
                });
            })
            .then(function () {
                const el = elementFor(modalVaschettaId);
                if (el) el.remove();
                state.vaschette.delete(modalVaschettaId);
                closeModal();
            })
            .catch(function (err) {
                alert(err.message || "Errore durante la rimozione.");
            });
    });

    // ---- Tooltip (costruito via DOM, mai innerHTML con dati non fidati) ----
    function showTooltip(v, event) {
        const info = gruppiMap.get(v.gruppo);
        if (!info) return;

        tooltip.textContent = "";

        const title = document.createElement("strong");
        title.textContent = v.gruppo;
        tooltip.appendChild(title);

        if (info.descrizione) {
            const desc = document.createElement("div");
            desc.textContent = info.descrizione;
            tooltip.appendChild(desc);
        }

        const list = document.createElement("ul");
        info.codici.forEach(function (codice) {
            const li = document.createElement("li");
            li.textContent = codice;
            list.appendChild(li);
        });
        tooltip.appendChild(list);

        tooltip.hidden = false;
        positionTooltip(event);
    }

    function positionTooltip(event) {
        const offset = 14;
        let left = event.clientX + offset;
        let top = event.clientY + offset;
        const maxLeft = window.innerWidth - 300;
        const maxTop = window.innerHeight - 220;
        if (left > maxLeft) left = event.clientX - 300 - offset;
        if (top > maxTop) top = event.clientY - 220 - offset;
        tooltip.style.left = Math.max(0, left) + "px";
        tooltip.style.top = Math.max(0, top) + "px";
    }

    function hideTooltip() {
        tooltip.hidden = true;
    }

    // ---- Toast di notifica ----
    let toastTimer = null;

    function showToast(message, durata) {
        clearTimeout(toastTimer);
        searchToast.textContent = message;
        searchToast.hidden = false;
        if (durata) {
            toastTimer = setTimeout(hideToast, durata);
        }
    }

    function hideToast() {
        searchToast.hidden = true;
    }

    // ---- Ricerca: prima nel supporto attivo, poi in tutti gli altri della commessa ----
    function clearTabBadges() {
        document.querySelectorAll(".contenitore-tab").forEach(function (tab) {
            tab.classList.remove("tab-match");
            const icon = tab.querySelector(".tab-match-icon");
            if (icon) icon.hidden = true;
        });
    }

    let autoSwitchTimer = null;

    searchInput.addEventListener("input", function () {
        clearTimeout(autoSwitchTimer);
        const query = searchInput.value.trim().toLowerCase();
        pallet.querySelectorAll(".vaschetta").forEach(function (el) { el.classList.remove("highlight"); });
        clearTabBadges();
        hideToast();
        if (!query) return;

        const gruppiTrovati = new Set();
        righeData.forEach(function (r) {
            if (r.codice && r.gruppo && r.codice.toLowerCase().includes(query)) {
                gruppiTrovati.add(r.gruppo);
            }
        });
        if (!gruppiTrovati.size) return;

        let trovatoQui = false;
        state.vaschette.forEach(function (v) {
            if (v.gruppo && gruppiTrovati.has(v.gruppo)) {
                const el = elementFor(v.id);
                if (el) { el.classList.add("highlight"); trovatoQui = true; }
            }
        });
        if (trovatoQui) return;

        const altrove = ricercaGlobale.filter(function (r) {
            return gruppiTrovati.has(r.gruppo) && r.contenitore_id !== contenitoreId;
        });
        if (!altrove.length) return;

        const perContenitore = new Map();
        altrove.forEach(function (r) {
            if (!perContenitore.has(r.contenitore_id)) perContenitore.set(r.contenitore_id, r.vaschetta_id);
        });

        perContenitore.forEach(function (_vaschettaId, contId) {
            const tab = document.querySelector('.contenitore-tab[data-contenitore-id="' + contId + '"]');
            if (!tab) return;
            tab.classList.add("tab-match");
            const icon = tab.querySelector(".tab-match-icon");
            if (icon) icon.hidden = false;
        });

        const primaCoppia = perContenitore.entries().next().value;
        const primoContenitoreId = primaCoppia[0];
        const primaVaschettaId = primaCoppia[1];
        const nomeSupporto = nomeContenitoreMap.get(primoContenitoreId) || "un altro supporto";

        showToast("Articolo trovato in: " + nomeSupporto + " — passaggio automatico...");

        autoSwitchTimer = setTimeout(function () {
            let url = mappaBase + "/" + primoContenitoreId + "?evidenzia=" + primaVaschettaId;
            if (vistaLettura) url += "&vista=1";
            window.location.href = url;
        }, 900);
    });

    // ---- Evidenziazione al carico pagina, se si arriva da una ricerca su un altro supporto ----
    (function evidenziaDaRicerca() {
        const params = new URLSearchParams(window.location.search);
        const evidenziaId = params.get("evidenzia");
        if (!evidenziaId) return;

        const el = elementFor(Number(evidenziaId));
        if (el) {
            el.classList.add("highlight");
            el.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
            showToast("Articolo trovato qui.", 2500);
        }

        const url = new URL(window.location.href);
        url.searchParams.delete("evidenzia");
        history.replaceState({}, "", url.toString());
    })();

    // ---- Modale "Aggiungi Supporto" ----
    const supportoModalOverlay = document.getElementById("supporto-modal-overlay");
    const supportoTipo = document.getElementById("supporto-tipo");
    const supportoEtichetta = document.getElementById("supporto-etichetta");
    const supportoError = document.getElementById("supporto-modal-error");
    const btnAggiungiSupporto = document.getElementById("btn-aggiungi-supporto");
    const supportoModalCancel = document.getElementById("supporto-modal-cancel");
    const supportoModalCrea = document.getElementById("supporto-modal-crea");

    function openSupportoModal() {
        supportoTipo.value = "bancale";
        supportoEtichetta.value = "";
        supportoError.hidden = true;
        supportoModalOverlay.hidden = false;
    }

    function closeSupportoModal() {
        supportoModalOverlay.hidden = true;
    }

    if (!vistaLettura) {
        btnAggiungiSupporto.addEventListener("click", openSupportoModal);
        supportoModalCancel.addEventListener("click", closeSupportoModal);
        supportoModalOverlay.addEventListener("click", function (event) {
            if (event.target === supportoModalOverlay) closeSupportoModal();
        });

        supportoModalCrea.addEventListener("click", function () {
            fetch(contenitoriUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tipo: supportoTipo.value, etichetta: supportoEtichetta.value }),
            })
                .then(function (response) {
                    return response.json().then(function (data) {
                        if (!response.ok) throw new Error(data.error || "Errore durante la creazione del supporto.");
                        return data;
                    });
                })
                .then(function (nuovi) {
                    window.location.href = mappaBase + "/" + nuovi[0].id;
                })
                .catch(function (err) {
                    supportoError.hidden = false;
                    supportoError.textContent = err.message || "Errore durante la creazione del supporto.";
                });
        });

        const btnEliminaSupporto = document.getElementById("btn-elimina-supporto");
        if (btnEliminaSupporto) {
            btnEliminaSupporto.addEventListener("click", function () {
                if (!confirm("Eliminare questo supporto e tutte le vaschette che contiene?")) return;
                fetch(eliminaSupportoBase + "/" + contenitoreId + "/elimina", { method: "POST" })
                    .then(function (response) {
                        return response.json().then(function (data) {
                            if (!response.ok) throw new Error(data.error || "Errore durante l'eliminazione.");
                            return data;
                        });
                    })
                    .then(function () {
                        window.location.href = mappaBase;
                    })
                    .catch(function (err) {
                        alert(err.message || "Errore durante l'eliminazione del supporto.");
                    });
            });
        }
    }

    // ---- Stampa Etichette Gruppi (riusa lo script "Con Barcode" esistente) ----
    const btnStampaEtichette = document.getElementById("btn-stampa-etichette");
    btnStampaEtichette.addEventListener("click", function () {
        const pendingTab = openPendingTab();
        btnStampaEtichette.disabled = true;

        fetch(stampaEtichetteUrl, { method: "POST" })
            .then(function (response) {
                return response.json().then(function (data) {
                    if (!response.ok) throw new Error(data.error || "Errore durante la generazione.");
                    return data;
                });
            })
            .then(function (data) {
                pollJob(jobStatusBase, data.job_id, function (job) {
                    btnStampaEtichette.disabled = false;
                    if (pendingTab && !pendingTab.closed) {
                        pendingTab.location.href = job.download_url;
                    } else {
                        window.open(job.download_url, "_blank");
                    }
                }, function (message) {
                    btnStampaEtichette.disabled = false;
                    if (pendingTab) pendingTab.close();
                    alert(message);
                });
            })
            .catch(function (err) {
                btnStampaEtichette.disabled = false;
                if (pendingTab) pendingTab.close();
                alert(err.message || "Errore durante la generazione delle etichette.");
            });
    });

    // ---- Modale "Stampa Cartello A4" (riusa lo script Cartelli esistente) ----
    const cartelloModalOverlay = document.getElementById("cartello-modal-overlay");
    const cartelloImmagine = document.getElementById("cartello-immagine");
    const cartelloNumeroBancale = document.getElementById("cartello-numero-bancale");
    const cartelloError = document.getElementById("cartello-modal-error");
    const btnStampaCartello = document.getElementById("btn-stampa-cartello");
    const cartelloModalCancel = document.getElementById("cartello-modal-cancel");
    const cartelloModalGenera = document.getElementById("cartello-modal-genera");

    function closeCartelloModal() {
        cartelloModalOverlay.hidden = true;
    }

    btnStampaCartello.addEventListener("click", function () {
        cartelloError.hidden = true;
        cartelloModalOverlay.hidden = false;
    });
    cartelloModalCancel.addEventListener("click", closeCartelloModal);
    cartelloModalOverlay.addEventListener("click", function (event) {
        if (event.target === cartelloModalOverlay) closeCartelloModal();
    });

    cartelloModalGenera.addEventListener("click", function () {
        const numero = cartelloNumeroBancale.value.trim();
        if (!numero) {
            cartelloError.hidden = false;
            cartelloError.textContent = "Inserisci il numero o il nome del supporto.";
            return;
        }

        const pendingTab = openPendingTab();
        closeCartelloModal();

        fetch(stampaCartelloUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ immagine: cartelloImmagine.value, numero_bancale: numero }),
        })
            .then(function (response) {
                return response.json().then(function (data) {
                    if (!response.ok) throw new Error(data.error || "Errore durante la generazione.");
                    return data;
                });
            })
            .then(function (data) {
                pollJob(jobStatusBase, data.job_id, function (job) {
                    if (pendingTab && !pendingTab.closed) {
                        pendingTab.location.href = job.download_url;
                    } else {
                        window.open(job.download_url, "_blank");
                    }
                }, function (message) {
                    if (pendingTab) pendingTab.close();
                    alert(message);
                });
            })
            .catch(function (err) {
                if (pendingTab) pendingTab.close();
                alert(err.message || "Errore durante la generazione del cartello.");
            });
    });
});
