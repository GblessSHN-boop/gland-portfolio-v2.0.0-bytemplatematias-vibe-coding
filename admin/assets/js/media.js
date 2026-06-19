const state = {
    mediaFiles: [],
    editingMediaId: null,
};

const form = document.querySelector("[data-media-form]");
const listElement = document.querySelector("[data-media-list]");
const statusElement = document.querySelector("[data-page-status]");
const refreshButton = document.querySelector("[data-refresh-media]");
const resetButton = document.querySelector("[data-reset-media-form]");
const submitButton = document.querySelector("[data-submit-media]");

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

function resolveMediaPath(path) {
    if (!path) {
        return "";
    }

    if (path.startsWith("uploads/") || path.startsWith("assets/")) {
        return `../${path}`;
    }

    return path;
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

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();

        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error("Failed to read selected file."));
        reader.readAsDataURL(file);
    });
}

function getSelectedFile() {
    return form.elements.file.files?.[0] || null;
}

function setFormMedia(mediaFile) {
    state.editingMediaId = mediaFile?.id || null;

    form.elements.title.value = mediaFile?.title || "";
    form.elements.alt_text.value = mediaFile?.alt_text || "";
    form.elements.media_type.value = mediaFile?.media_type || "image";
    form.elements.is_active.checked = mediaFile?.is_active ?? true;

    form.elements.file.required = !state.editingMediaId;
    form.elements.file.value = "";

    submitButton.textContent = state.editingMediaId ? "Update Metadata" : "Upload Media";
}

function renderMediaFiles() {
    if (!listElement) {
        return;
    }

    if (!state.mediaFiles.length) {
        listElement.innerHTML = `
            <div class="gland-card gland-empty">
                No media files yet. Upload an image or video.
            </div>
        `;
        return;
    }

    listElement.innerHTML = state.mediaFiles.map((mediaFile) => {
        const mediaPath = resolveMediaPath(mediaFile.file_path);
        const preview = mediaFile.media_type === "video"
            ? `<video class="gland-media-preview" src="${escapeHtml(mediaPath)}" muted controls></video>`
            : `<img class="gland-media-preview" src="${escapeHtml(mediaPath)}" alt="${escapeHtml(mediaFile.alt_text || mediaFile.title)}">`;

        return `
            <article class="gland-card gland-media-card" data-media-id="${escapeHtml(mediaFile.id)}">
                ${preview}

                <h3 class="gland-media-title">${escapeHtml(mediaFile.title || mediaFile.file_name)}</h3>
                <p class="gland-media-meta">
                    ${escapeHtml(mediaFile.media_type)} · ${escapeHtml(mediaFile.file_path)} · ${escapeHtml(mediaFile.file_size)} bytes
                </p>
                <p class="gland-media-meta">
                    ${mediaFile.is_active ? "Active" : "Inactive"}
                </p>

                <div class="gland-actions">
                    <button class="gland-button secondary" data-action="edit">Edit Metadata</button>
                    <button class="gland-button danger" data-action="delete">Delete</button>
                </div>
            </article>
        `;
    }).join("");
}

async function loadMediaFiles() {
    setStatus("Loading media files...");

    try {
        const payload = await apiRequest("/api/media-files");
        state.mediaFiles = payload.data || [];
        renderMediaFiles();
        setStatus(`Loaded ${state.mediaFiles.length} media file(s) from MySQL.`);
    } catch (error) {
        listElement.innerHTML = `
            <div class="gland-card gland-error">
                ${escapeHtml(error.message)}
            </div>
        `;
        setStatus("Failed to load media files.", "error");
    }
}

async function saveMedia(event) {
    event.preventDefault();

    const file = getSelectedFile();

    try {
        if (state.editingMediaId) {
            const response = await apiRequest(`/api/media-files/${state.editingMediaId}`, {
                method: "PATCH",
                body: JSON.stringify({
                    title: form.elements.title.value,
                    alt_text: form.elements.alt_text.value,
                    is_active: form.elements.is_active.checked,
                }),
            });

            state.mediaFiles = state.mediaFiles.map((mediaFile) => {
                if (Number(mediaFile.id) === Number(state.editingMediaId)) {
                    return response.data;
                }

                return mediaFile;
            });

            setFormMedia(null);
            renderMediaFiles();
            setStatus(`Media file #${response.data.id} updated.`);
            return;
        }

        if (!file) {
            setStatus("Choose a file before uploading.", "error");
            return;
        }

        const fileBase64 = await fileToBase64(file);

        const response = await apiRequest("/api/media-files", {
            method: "POST",
            body: JSON.stringify({
                title: form.elements.title.value,
                alt_text: form.elements.alt_text.value,
                media_type: form.elements.media_type.value,
                file_name: file.name,
                mime_type: file.type,
                file_base64: fileBase64,
                is_active: form.elements.is_active.checked,
            }),
        });

        state.mediaFiles = [response.data, ...state.mediaFiles];
        setFormMedia(null);
        renderMediaFiles();
        setStatus(`Media file #${response.data.id} uploaded.`);
    } catch (error) {
        setStatus(error.message, "error");
    }
}

async function deleteMedia(mediaId) {
    const isConfirmed = window.confirm(`Delete media file #${mediaId}? This will remove the file from uploads too.`);

    if (!isConfirmed) {
        return;
    }

    try {
        await apiRequest(`/api/media-files/${mediaId}`, {
            method: "DELETE",
        });

        state.mediaFiles = state.mediaFiles.filter((mediaFile) => Number(mediaFile.id) !== Number(mediaId));
        renderMediaFiles();
        setStatus(`Media file #${mediaId} deleted.`);
    } catch (error) {
        setStatus(error.message, "error");
    }
}

listElement?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");

    if (!button) {
        return;
    }

    const card = button.closest("[data-media-id]");
    const mediaId = Number(card?.dataset.mediaId);
    const action = button.dataset.action;
    const mediaFile = state.mediaFiles.find((item) => Number(item.id) === mediaId);

    if (!mediaFile) {
        return;
    }

    if (action === "edit") {
        setFormMedia(mediaFile);
        window.scrollTo(0, 0);
        return;
    }

    if (action === "delete") {
        deleteMedia(mediaId);
    }
});

form?.addEventListener("submit", saveMedia);

resetButton?.addEventListener("click", () => {
    setFormMedia(null);
    setStatus("Media form reset.");
});

refreshButton?.addEventListener("click", () => {
    loadMediaFiles();
});

setFormMedia(null);
loadMediaFiles();