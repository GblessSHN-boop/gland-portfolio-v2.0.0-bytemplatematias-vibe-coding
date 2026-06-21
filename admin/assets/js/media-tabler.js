(function () {
  "use strict";

  const API = "/api/media-files";
  const form = document.getElementById("mediaForm");
  const list = document.getElementById("mediaList");
  const statusEl = document.getElementById("mediaStatus");

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
    const data = payload && (payload.data || payload.media_files || payload.mediaFiles || payload.items || payload);
    return Array.isArray(data) ? data : [];
  }

  async function request(url, options = {}) {
    const response = await fetch(url, {
      credentials: "include",
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

  async function loadMedia() {
    status("Loading media...");
    const payload = await request(API);
    const items = normalize(payload);

    if (!items.length) {
      list.innerHTML = '<div class="gland-empty">No media files yet. Upload an image or video.</div>';
      status("Loaded 0 media file(s) from MySQL.");
      return;
    }

    list.innerHTML = items.map((item) => {
      const id = escapeHtml(item.id);
      const title = escapeHtml(item.title || item.original_name || item.file_name || "Untitled media");
      const type = escapeHtml(item.media_type || item.type || "media");
      const path = escapeHtml(item.file_path || item.path || item.url || "");

      return `
        <article class="gland-list-card">
          <h3 class="gland-list-card-title">${title}</h3>
          <p class="gland-list-card-meta">${type}</p>
          <p class="gland-list-card-meta">${path}</p>
          <div class="gland-list-card-actions">
            <button type="button" class="gland-btn gland-btn-danger" data-delete-media="${id}">Delete</button>
          </div>
        </article>
      `;
    }).join("");

    document.querySelectorAll("[data-delete-media]").forEach((button) => {
      button.addEventListener("click", () => deleteMedia(button.dataset.deleteMedia));
    });

    status(`Loaded ${items.length} media file(s) from MySQL.`);
  }

  async function deleteMedia(id) {
    if (!confirm("Delete this media file?")) return;

    await request(`${API}/${id}`, { method: "DELETE" });
    status("Media deleted.");
    await loadMedia();
  }

  async function uploadMedia(event) {
    event.preventDefault();

    const formData = new FormData(form);

    await request(API, {
      method: "POST",
      body: formData
    });

    form.reset();
    status("Media uploaded.");
    await loadMedia();
  }

  form.addEventListener("submit", uploadMedia);

  document.querySelectorAll("[data-refresh-page]").forEach((button) => {
    button.addEventListener("click", loadMedia);
  });

  loadMedia().catch((error) => status(error.message));
})();