(function () {
  "use strict";

  const API_URL = "/api/admin/activity?limit=100";

  const list = document.getElementById("activityList");
  const status = document.getElementById("activityStatus");
  const refreshButton = document.getElementById("refreshActivityButton");

  function setStatus(message) {
    if (status) status.textContent = message;
  }

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function humanizeAction(value) {
    return String(value || "activity")
      .replaceAll("_", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function iconFor(item) {
    const action = String(item.action || "");

    if (action.includes("login")) return "ti-login";
    if (action.includes("logout")) return "ti-logout";
    if (action.includes("delete")) return "ti-trash";
    if (action.includes("message")) return "ti-message";
    if (action.includes("update")) return "ti-pencil";
    return "ti-history";
  }

  function statusClass(item) {
    const status = String(item.status || "").toLowerCase();

    if (status === "failed" || status === "error") return "is-danger";
    if (status === "success") return "is-success";
    return "is-neutral";
  }

  function renderSummary(summary) {
    const data = summary || {};

    const total = document.querySelector("[data-activity-total]");
    const last24 = document.querySelector("[data-activity-24h]");
    const auth = document.querySelector("[data-activity-auth]");
    const message = document.querySelector("[data-activity-message]");

    if (total) total.textContent = data.total_events ?? 0;
    if (last24) last24.textContent = data.events_24h ?? 0;
    if (auth) auth.textContent = data.auth_events ?? 0;
    if (message) message.textContent = data.message_events ?? 0;
  }

  function renderItems(items) {
    if (!list) return;

    if (!items.length) {
      list.innerHTML = '<div class="gland-empty">No admin activity recorded yet.</div>';
      return;
    }

    list.innerHTML = items.map((item) => {
      const action = escapeHtml(humanizeAction(item.action));
      const description = escapeHtml(item.description || "Activity recorded.");
      const entity = escapeHtml(item.entity_type || item.source || "system");
      const entityId = escapeHtml(item.entity_id || "");
      const createdAt = escapeHtml(item.created_at || "-");
      const ip = escapeHtml(item.ip_address || "-");
      const actor = escapeHtml(item.admin_username || "System");
      const source = escapeHtml(item.source || "activity");
      const icon = escapeHtml(iconFor(item));
      const badgeClass = escapeHtml(statusClass(item));
      const statusText = escapeHtml(item.status || "recorded");

      return `
        <article class="gland-activity-item">
          <div class="gland-activity-icon">
            <i class="ti ${icon}"></i>
          </div>

          <div class="gland-activity-content">
            <div class="gland-activity-head">
              <div>
                <h3 class="gland-activity-title">${action}</h3>
                <p class="gland-activity-meta">${createdAt} · ${actor} · IP ${ip}</p>
              </div>

              <span class="gland-activity-badge ${badgeClass}">${statusText}</span>
            </div>

            <p class="gland-activity-description">${description}</p>

            <div class="gland-activity-foot">
              <span>${source}</span>
              <span>${entity}${entityId ? " #" + entityId : ""}</span>
            </div>
          </div>
        </article>
      `;
    }).join("");
  }

  async function loadActivity() {
    setStatus("Loading activity...");

    const response = await fetch(API_URL, {
      credentials: "include",
      headers: { "Accept": "application/json" }
    });

    if (response.status === 401) {
      window.location.href = "login.html";
      return;
    }

    const payload = await response.json().catch(() => ({}));

    if (!response.ok || payload.success === false) {
      throw new Error(payload.message || payload.error || "Failed to load activity.");
    }

    const data = payload.data || {};
    const items = Array.isArray(data.items) ? data.items : [];

    renderSummary(data.summary || {});
    renderItems(items);

    setStatus(`Loaded ${items.length} activity event(s).`);
  }

  function boot() {
    if (refreshButton) {
      refreshButton.addEventListener("click", () => {
        loadActivity().catch((error) => setStatus(error.message));
      });
    }

    loadActivity().catch((error) => setStatus(error.message));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();