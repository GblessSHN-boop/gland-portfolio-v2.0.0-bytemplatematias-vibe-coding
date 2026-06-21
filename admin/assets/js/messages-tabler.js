(function () {
  "use strict";

  const API = "/api/messages";
  const REFRESH_MS = 3000;

  let messages = [];
  let activeFilter = "new";
  let timer = null;

  const list = document.getElementById("messagesList");
  const statusEl = document.getElementById("messagesStatus");

  function status(message) {
    if (statusEl) statusEl.textContent = message;
  }

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function normalizeStatus(value) {
    const status = String(value || "new").trim().toLowerCase();
    if (["read", "approved", "rejected", "archived"].includes(status)) return status;
    return "new";
  }

  function normalizePayload(payload) {
    const data = payload && (payload.data || payload.messages || payload.items || payload);
    return Array.isArray(data) ? data : [];
  }

  function isUserEditing() {
    const active = document.activeElement;
    if (!active) return false;

    const tag = active.tagName ? active.tagName.toLowerCase() : "";
    return tag === "input" || tag === "textarea" || tag === "select" || active.isContentEditable;
  }

  async function request(url, options = {}) {
    const response = await fetch(url, {
      credentials: "include",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json",
        ...(options.headers || {})
      },
      ...options
    });

    if (response.status === 401) {
      window.location.href = "login.html";
      return null;
    }

    const payload = await response.json().catch(() => ({}));

    if (!response.ok || payload.success === false) {
      throw new Error(payload.error || payload.message || "Request failed");
    }

    return payload;
  }

  function messageMatchesFilter(message) {
    const current = normalizeStatus(message.status);

    if (activeFilter === "new") {
      return current === "new";
    }

    return current === activeFilter;
  }

  function renderMessages() {
    const filtered = messages.filter(messageMatchesFilter);

    if (!filtered.length) {
      list.innerHTML = `<div class="gland-message-empty">No ${escapeHtml(activeFilter)} messages.</div>`;
      return;
    }

    list.innerHTML = filtered.map((message) => {
      const id = escapeHtml(message.id);
      const name = escapeHtml(message.name || "Unknown Sender");
      const email = escapeHtml(message.email || "No email");
      const created = escapeHtml(message.created_at || message.createdAt || "");
      const subject = escapeHtml(message.subject || "Website Contact Message");
      const text = escapeHtml(message.message || message.content || "");
      const note = escapeHtml(message.admin_note || message.adminNote || "");
      const current = normalizeStatus(message.status);

      return `
        <article class="gland-message-card" data-message-id="${id}">
          <div class="gland-message-head">
            <div>
              <h2 class="gland-message-name">${name}</h2>
              <p class="gland-message-meta">${email} <span aria-hidden="true">•</span> ${created}</p>
            </div>
            <span class="gland-message-badge">${current}</span>
          </div>

          <div class="gland-message-content">
            <p class="gland-message-content-label">${subject}</p>
            <p class="gland-message-text">${text}</p>
          </div>

          <div class="gland-message-actions">
            <input class="gland-message-note" data-message-note="${id}" value="${note}" placeholder="Add internal admin note...">
            <button type="button" class="gland-btn" data-message-action="read" data-message-id="${id}">Read</button>
            <button type="button" class="gland-btn gland-btn-primary" data-message-action="approved" data-message-id="${id}">Approve</button>
            <button type="button" class="gland-btn" data-message-action="rejected" data-message-id="${id}">Reject</button>
            <button type="button" class="gland-btn gland-btn-danger" data-message-action="delete" data-message-id="${id}">Delete</button>
          </div>
        </article>
      `;
    }).join("");

    document.querySelectorAll("[data-message-action]").forEach((button) => {
      button.addEventListener("click", () => handleAction(button.dataset.messageId, button.dataset.messageAction));
    });
  }

  async function loadMessages(silent = false) {
    if (isUserEditing()) return;

    if (!silent) status("Loading messages...");

    const payload = await request(API);
    messages = normalizePayload(payload);
    renderMessages();
    status(`Loaded ${messages.length} message(s) from MySQL.`);
  }

  async function handleAction(id, action) {
    if (!id) return;

    if (action === "delete") {
      if (!confirm("Delete this message permanently?")) return;

      await request(`${API}/${id}`, { method: "DELETE" });
      status("Message deleted.");
      await loadMessages(true);
      return;
    }

    const noteInput = document.querySelector(`[data-message-note="${CSS.escape(String(id))}"]`);
    const adminNote = noteInput ? noteInput.value.trim() : "";

    await request(`${API}/${id}`, {
      method: "PATCH",
      body: JSON.stringify({
        status: action,
        admin_note: adminNote
      })
    });

    status(`Message marked as ${action}.`);
    await loadMessages(true);
  }

  function bindTabs() {
    document.querySelectorAll("[data-message-filter]").forEach((button) => {
      button.addEventListener("click", () => {
        activeFilter = button.dataset.messageFilter || "new";

        document.querySelectorAll("[data-message-filter]").forEach((item) => {
          item.classList.toggle("is-active", item === button);
        });

        renderMessages();
      });
    });
  }

  function boot() {
    bindTabs();

    loadMessages().catch((error) => status(error.message));

    timer = window.setInterval(() => {
      if (!document.hidden && !isUserEditing()) {
        loadMessages(true).catch((error) => status(error.message));
      }
    }, REFRESH_MS);

    window.addEventListener("beforeunload", () => {
      if (timer) window.clearInterval(timer);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();