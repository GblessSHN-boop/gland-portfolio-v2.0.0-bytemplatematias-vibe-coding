(function () {
  "use strict";

  const API = "/api/highlights";
  let highlights = [];

  const $ = (id) => document.getElementById(id);

  function text(value) {
    return String(value || "").trim();
  }

  function status(message) {
    $("highlightsStatus").textContent = message;
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
    const data = payload && (payload.data || payload.highlights || payload.items || payload);
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

  function resetForm() {
    $("highlightId").value = "";
    $("highlightForm").reset();
    $("highlightDisplayOrder").value = "0";
    $("highlightIsActive").value = "1";
    $("highlightFormTitle").textContent = "Create Highlight";
    $("highlightSubmitButton").textContent = "Create Highlight";
  }

  function payloadFromForm() {
    return {
      title: text($("highlightTitle").value),
      subtitle: text($("highlightSubtitle").value),
      year: text($("highlightYear").value),
      highlight_url: text($("highlightUrl").value),
      display_order: Number($("highlightDisplayOrder").value || 0),
      is_active: $("highlightIsActive").value === "1"
    };
  }

  function editHighlight(id) {
    const item = highlights.find((highlight) => String(highlight.id) === String(id));
    if (!item) return;

    $("highlightId").value = item.id || "";
    $("highlightTitle").value = item.title || "";
    $("highlightSubtitle").value = item.subtitle || "";
    $("highlightYear").value = item.year || "";
    $("highlightUrl").value = item.highlight_url || item.highlightUrl || "";
    $("highlightDisplayOrder").value = item.display_order ?? item.displayOrder ?? 0;
    $("highlightIsActive").value = item.is_active === false || item.is_active === 0 ? "0" : "1";

    $("highlightFormTitle").textContent = "Edit Highlight";
    $("highlightSubmitButton").textContent = "Save Changes";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function deleteHighlight(id) {
    if (!confirm("Delete this highlight?")) return;

    await request(`${API}/${id}`, { method: "DELETE" });
    status("Highlight deleted.");
    await loadHighlights();
  }

  function renderHighlights() {
    const list = $("highlightsList");

    if (!highlights.length) {
      list.innerHTML = '<div class="gland-empty">No highlights yet. Create your first highlight from the form.</div>';
      return;
    }

    list.innerHTML = highlights.map((item) => {
      const id = escapeHtml(item.id);
      const title = escapeHtml(item.title || "Untitled Highlight");
      const subtitle = escapeHtml(item.subtitle || "No subtitle");
      const year = escapeHtml(item.year || "No year");
      const url = escapeHtml(item.highlight_url || item.highlightUrl || "No URL");

      return `
        <article class="gland-list-card">
          <h3 class="gland-list-card-title">${title}</h3>
          <p class="gland-list-card-meta">${subtitle}</p>
          <p class="gland-list-card-meta">${year}</p>
          <p class="gland-list-card-meta">${url}</p>
          <div class="gland-list-card-actions">
            <button type="button" class="gland-btn" data-edit-highlight="${id}">Edit</button>
            <button type="button" class="gland-btn gland-btn-danger" data-delete-highlight="${id}">Delete</button>
          </div>
        </article>
      `;
    }).join("");

    document.querySelectorAll("[data-edit-highlight]").forEach((button) => {
      button.addEventListener("click", () => editHighlight(button.dataset.editHighlight));
    });

    document.querySelectorAll("[data-delete-highlight]").forEach((button) => {
      button.addEventListener("click", () => deleteHighlight(button.dataset.deleteHighlight));
    });
  }

  async function loadHighlights() {
    status("Loading highlights...");
    const payload = await request(API);
    highlights = normalize(payload);
    renderHighlights();
    status(`Loaded ${highlights.length} highlight(s) from MySQL.`);
  }

  async function saveHighlight(event) {
    event.preventDefault();

    const id = $("highlightId").value;
    const payload = payloadFromForm();

    if (!payload.title) {
      status("Highlight title is required.");
      return;
    }

    if (id) {
      await request(`${API}/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload)
      });
      status("Highlight updated.");
    } else {
      await request(API, {
        method: "POST",
        body: JSON.stringify(payload)
      });
      status("Highlight created.");
    }

    resetForm();
    await loadHighlights();
  }

  function boot() {
    $("highlightForm").addEventListener("submit", saveHighlight);
    $("highlightResetButton").addEventListener("click", resetForm);

    document.querySelectorAll("[data-refresh-page]").forEach((button) => {
      button.addEventListener("click", loadHighlights);
    });

    loadHighlights().catch((error) => status(error.message));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();