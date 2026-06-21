(function () {
  "use strict";

  const form = document.querySelector("[data-singleton-api]");
  const statusEl = document.querySelector("[data-page-status]");

  if (!form) return;

  const api = form.dataset.singletonApi;

  function status(message) {
    if (statusEl) statusEl.textContent = message;
  }

  function normalize(payload) {
    return payload && (payload.data || payload.item || payload.result || payload);
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

  function fillForm(data) {
    if (!data) return;

    form.querySelectorAll("[name]").forEach((field) => {
      const name = field.name;
      const value = data[name];

      if (value === undefined || value === null) return;

      if (field.type === "checkbox") {
        field.checked = Boolean(value);
      } else {
        field.value = value;
      }
    });
  }

  function collectForm() {
    const data = {};

    form.querySelectorAll("[name]").forEach((field) => {
      if (field.type === "checkbox") {
        data[field.name] = field.checked;
      } else if (field.type === "number") {
        data[field.name] = Number(field.value || 0);
      } else {
        data[field.name] = String(field.value || "").trim();
      }
    });

    return data;
  }

  async function loadData() {
    status("Loading data...");
    const payload = await request(api);
    fillForm(normalize(payload));
    status("Data loaded from MySQL.");
  }

  async function saveData(event) {
    event.preventDefault();

    const data = collectForm();

    await request(api, {
      method: "PATCH",
      body: JSON.stringify(data)
    });

    status("Changes saved.");
    await loadData();
  }

  form.addEventListener("submit", saveData);

  document.querySelectorAll("[data-refresh-page]").forEach((button) => {
    button.addEventListener("click", loadData);
  });

  loadData().catch((error) => status(error.message));
})();