const state = {
    messages: [],
    isLoading: false,
};

const listElement = document.querySelector("[data-message-list]");
const refreshButton = document.querySelector("[data-refresh-messages]");
const statusElement = document.querySelector("[data-page-status]");

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

function renderMessages() {
    if (!listElement) {
        return;
    }

    if (state.isLoading) {
        listElement.innerHTML = `
            <div class="gland-card gland-empty">
                Loading messages from MySQL...
            </div>
        `;
        return;
    }

    if (!state.messages.length) {
        listElement.innerHTML = `
            <div class="gland-card gland-empty">
                No contact messages yet.
            </div>
        `;
        return;
    }

    listElement.innerHTML = state.messages.map((message) => `
        <article class="gland-card gland-message-card" data-message-id="${escapeHtml(message.id)}">
            <div class="gland-message-top">
                <div>
                    <h2 class="gland-message-name">${escapeHtml(message.name)}</h2>
                    <p class="gland-message-meta">
                        ${escapeHtml(message.email)} · ${escapeHtml(message.created_at)}
                    </p>
                </div>
                <span class="gland-status">${escapeHtml(message.status)}</span>
            </div>

            <p class="gland-message-subject">${escapeHtml(message.subject || "No subject")}</p>
            <p class="gland-message-body">${escapeHtml(message.message)}</p>

            <label>
                <strong>Admin note</strong>
                <textarea class="gland-note" data-admin-note>${escapeHtml(message.admin_note || "")}</textarea>
            </label>

            <div class="gland-actions">
                <button class="gland-button secondary" data-action="read">Mark Read</button>
                <button class="gland-button lime" data-action="approved">Approve</button>
                <button class="gland-button secondary" data-action="rejected">Reject</button>
                <button class="gland-button secondary" data-action="archived">Archive</button>
                <button class="gland-button danger" data-action="delete">Delete</button>
            </div>
        </article>
    `).join("");
}

async function loadMessages() {
    state.isLoading = true;
    renderMessages();
    setStatus("Loading inbox...");

    try {
        const payload = await apiRequest("/api/messages");
        state.messages = payload.data || [];
        setStatus(`Loaded ${state.messages.length} message(s) from MySQL.`);
    } catch (error) {
        listElement.innerHTML = `
            <div class="gland-card gland-error">
                ${escapeHtml(error.message)}
            </div>
        `;
        setStatus("Failed to load messages.", "error");
    } finally {
        state.isLoading = false;
        renderMessages();
    }
}

async function updateMessage(messageId, status, adminNote) {
    setStatus(`Updating message #${messageId}...`);

    const payload = await apiRequest(`/api/messages/${messageId}`, {
        method: "PATCH",
        body: JSON.stringify({
            status,
            admin_note: adminNote,
        }),
    });

    const updatedMessage = payload.data;

    state.messages = state.messages.map((message) => {
        if (Number(message.id) === Number(messageId)) {
            return updatedMessage;
        }

        return message;
    });

    renderMessages();
    setStatus(`Message #${messageId} updated.`);
}

async function deleteMessage(messageId) {
    const isConfirmed = window.confirm(`Delete message #${messageId}?`);

    if (!isConfirmed) {
        return;
    }

    setStatus(`Deleting message #${messageId}...`);

    await apiRequest(`/api/messages/${messageId}`, {
        method: "DELETE",
    });

    state.messages = state.messages.filter((message) => Number(message.id) !== Number(messageId));
    renderMessages();
    setStatus(`Message #${messageId} deleted.`);
}

listElement?.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");

    if (!button) {
        return;
    }

    const card = button.closest("[data-message-id]");
    const messageId = card?.dataset.messageId;
    const action = button.dataset.action;
    const adminNote = card?.querySelector("[data-admin-note]")?.value || "";

    if (!messageId) {
        return;
    }

    try {
        if (action === "delete") {
            await deleteMessage(messageId);
            return;
        }

        await updateMessage(messageId, action, adminNote);
    } catch (error) {
        setStatus(error.message, "error");
    }
});

refreshButton?.addEventListener("click", () => {
    loadMessages();
});

loadMessages();