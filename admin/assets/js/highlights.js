const state = {
    highlights: [],
    editingHighlightId: null,
    isLoading: false,
};

const form = document.querySelector("[data-highlight-form]");
const listElement = document.querySelector("[data-highlight-list]");
const statusElement = document.querySelector("[data-page-status]");
const refreshButton = document.querySelector("[data-refresh-highlights]");
const resetButton = document.querySelector("[data-reset-highlight-form]");
const submitButton = document.querySelector("[data-submit-highlight]");

function setStatus(message, type = "info") {
    if (!statusElement) {
        return;
    }

    statusElement.textContent = message || "";
    statusElement.dataset.type = type;
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

async function apiRequest(path, options = {}) {
    const response = await fetch(path, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
        ...options,
    });

    const payload = await response.json().catch(() => ({
        success: false,
        message: "Invalid JSON response.",
    }));

    if (!response.ok || payload.success === false) {
        throw new Error(payload.message || "Request failed.");
    }

    return payload;
}

function getFormPayload() {
    const formData = new FormData(form);

    return {
        title: formData.get("title"),
        subtitle: formData.get("subtitle"),
        year_label: formData.get("year_label"),
        highlight_url: formData.get("highlight_url"),
        display_order: Number(formData.get("display_order") || 0),
        is_active: formData.get("is_active") === "on",
    };
}

function setFormHighlight(highlight) {
    state.editingHighlightId = highlight?.id || null;

    form.elements.title.value = highlight?.title || "";
    form.elements.subtitle.value = highlight?.subtitle || "";
    form.elements.year_label.value = highlight?.year_label || "";
    form.elements.highlight_url.value = highlight?.highlight_url || "";
    form.elements.display_order.value = highlight?.display_order ?? 0;
    form.elements.is_active.checked = highlight?.is_active ?? true;

    submitButton.textContent = state.editingHighlightId ? "Update Highlight" : "Create Highlight";
}

function renderHighlights() {
    if (!listElement) {
        return;
    }

    if (state.isLoading) {
        listElement.innerHTML = `
            <div class="gland-card gland-empty">
                Loading highlights from MySQL...
            </div>
        `;
        return;
    }

    if (!state.highlights.length) {
        listElement.innerHTML = `
            <div class="gland-card gland-empty">
                No highlights yet. Create the first selected highlight.
            </div>
        `;
        return;
    }

    listElement.innerHTML = state.highlights.map((highlight) => `
        <article class="gland-card gland-highlight-card" data-highlight-id="${escapeHtml(highlight.id)}">
            <div class="gland-highlight-top">
                <div>
                    <h3 class="gland-highlight-title">${escapeHtml(highlight.title)}</h3>
                    <p class="gland-highlight-subtitle">${escapeHtml(highlight.subtitle || "No subtitle")}</p>
                </div>
                <span class="gland-highlight-year">${escapeHtml(highlight.year_label || "No year")}</span>
            </div>

            <p class="gland-highlight-meta">
                Order ${escapeHtml(highlight.display_order)} · ${highlight.is_active ? "Active" : "Inactive"}
            </p>

            <div class="gland-actions">
                <button class="gland-button secondary" data-action="edit">Edit</button>
                <button class="gland-button danger" data-action="delete">Delete</button>
            </div>
        </article>
    `).join("");
}

async function loadHighlights() {
    state.isLoading = true;
    renderHighlights();
    setStatus("Loading highlights...");

    try {
        const payload = await apiRequest("/api/highlights");
        state.highlights = payload.data || [];
        setStatus(`Loaded ${state.highlights.length} highlight(s) from MySQL.`);
    } catch (error) {
        listElement.innerHTML = `
            <div class="gland-card gland-error">
                ${escapeHtml(error.message)}
            </div>
        `;
        setStatus("Failed to load highlights.", "error");
    } finally {
        state.isLoading = false;
        renderHighlights();
    }
}

async function saveHighlight(event) {
    event.preventDefault();

    const payload = getFormPayload();

    if (!payload.title.trim()) {
        setStatus("Highlight title is required.", "error");
        return;
    }

    try {
        if (state.editingHighlightId) {
            const response = await apiRequest(`/api/highlights/${state.editingHighlightId}`, {
                method: "PATCH",
                body: JSON.stringify(payload),
            });

            state.highlights = state.highlights.map((highlight) => {
                if (Number(highlight.id) === Number(state.editingHighlightId)) {
                    return response.data;
                }

                return highlight;
            });

            setStatus(`Highlight #${state.editingHighlightId} updated.`);
        } else {
            const response = await apiRequest("/api/highlights", {
                method: "POST",
                body: JSON.stringify(payload),
            });

            state.highlights = [response.data, ...state.highlights];
            setStatus(`Highlight #${response.data.id} created.`);
        }

        setFormHighlight(null);
        renderHighlights();
    } catch (error) {
        setStatus(error.message, "error");
    }
}

async function deleteHighlight(highlightId) {
    const isConfirmed = window.confirm(`Delete highlight #${highlightId}?`);

    if (!isConfirmed) {
        return;
    }

    try {
        await apiRequest(`/api/highlights/${highlightId}`, {
            method: "DELETE",
        });

        state.highlights = state.highlights.filter((highlight) => Number(highlight.id) !== Number(highlightId));
        renderHighlights();
        setStatus(`Highlight #${highlightId} deleted.`);
    } catch (error) {
        setStatus(error.message, "error");
    }
}

listElement?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");

    if (!button) {
        return;
    }

    const card = button.closest("[data-highlight-id]");
    const highlightId = Number(card?.dataset.highlightId);
    const action = button.dataset.action;
    const highlight = state.highlights.find((item) => Number(item.id) === highlightId);

    if (!highlight) {
        return;
    }

    if (action === "edit") {
        setFormHighlight(highlight);
        window.scrollTo(0, 0);
        return;
    }

    if (action === "delete") {
        deleteHighlight(highlightId);
    }
});

form?.addEventListener("submit", saveHighlight);

resetButton?.addEventListener("click", () => {
    setFormHighlight(null);
    setStatus("Highlight form reset.");
});

refreshButton?.addEventListener("click", () => {
    loadHighlights();
});

loadHighlights();