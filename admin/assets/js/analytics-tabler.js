(function () {
  "use strict";

  const eventsApi = "/api/analytics/events";
  const eventApi = "/api/analytics/event";
  const form = document.getElementById("analyticsForm");
  const tbody = document.getElementById("analyticsEventsBody");
  const statusEl = document.getElementById("analyticsStatus");

  function status(message) {
    statusEl.textContent = message;
  }

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function normalize(payload) {
    const data = payload && (payload.data || payload.events || payload.items || payload);
    return Array.isArray(data) ? data : [];
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

  async function loadEvents() {
    status("Loading analytics events...");
    const payload = await request(eventsApi);
    const items = normalize(payload);

    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="gland-empty">No analytics events yet.</td></tr>';
      status("Loaded 0 analytics event(s).");
      return;
    }

    tbody.innerHTML = items.slice(0, 80).map((item) => {
      return `
        <tr>
          <td>${escapeHtml(item.id)}</td>
          <td>${escapeHtml(item.event_type || item.type)}</td>
          <td>${escapeHtml(item.event_name || item.name)}</td>
          <td>${escapeHtml(item.page_path || item.page)}</td>
          <td>${escapeHtml(item.target_url || item.target)}</td>
          <td>${escapeHtml(item.created_at || item.createdAt)}</td>
        </tr>
      `;
    }).join("");

    status(`Loaded ${items.length} analytics event(s).`);
  }

  async function sendTestEvent(event) {
    event.preventDefault();

    const payload = {
      event_type: document.getElementById("eventType").value.trim(),
      event_name: document.getElementById("eventName").value.trim(),
      event_value: Number(document.getElementById("eventValue").value || 1),
      page_path: document.getElementById("pagePath").value.trim(),
      target_url: document.getElementById("targetUrl").value.trim()
    };

    await request(eventApi, {
      method: "POST",
      body: JSON.stringify(payload)
    });

    status("Test event sent.");
    await loadEvents();
  }

  form.addEventListener("submit", sendTestEvent);

  document.querySelectorAll("[data-refresh-page]").forEach((button) => {
    button.addEventListener("click", loadEvents);
  });

  loadEvents().catch((error) => status(error.message));
})();