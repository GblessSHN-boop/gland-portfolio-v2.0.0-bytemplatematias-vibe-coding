(function () {
  "use strict";

  const API = "/api/projects";
  let projects = [];

  const $ = (id) => document.getElementById(id);

  function text(value) {
    return String(value || "").trim();
  }

  function boolValue(id) {
    return $(id).value === "1";
  }

  function status(message) {
    $("projectsStatus").textContent = message;
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
    const data = payload && (payload.data || payload.projects || payload.items || payload);
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

  function getProjectPayload() {
    return {
      title: text($("projectTitle").value),
      category: text($("projectCategory").value),
      description: text($("projectDescription").value),
      image_path: text($("projectImagePath").value),
      technologies: text($("projectTechnologies").value),
      project_url: text($("projectUrl").value),
      repository_url: text($("projectRepositoryUrl").value),
      display_order: Number($("projectDisplayOrder").value || 0),
      is_featured: boolValue("projectIsFeatured"),
      is_active: boolValue("projectIsActive")
    };
  }

  function resetForm() {
    $("projectId").value = "";
    $("projectForm").reset();
    $("projectDisplayOrder").value = "0";
    $("projectIsFeatured").value = "0";
    $("projectIsActive").value = "1";
    $("projectFormTitle").textContent = "Create Project";
    $("projectSubmitButton").textContent = "Create Project";
  }

  function editProject(id) {
    const item = projects.find((project) => String(project.id) === String(id));
    if (!item) return;

    $("projectId").value = item.id || "";
    $("projectTitle").value = item.title || "";
    $("projectCategory").value = item.category || "";
    $("projectDescription").value = item.description || "";
    $("projectImagePath").value = item.image_path || item.imagePath || "";
    $("projectTechnologies").value = item.technologies || "";
    $("projectUrl").value = item.project_url || item.projectUrl || "";
    $("projectRepositoryUrl").value = item.repository_url || item.repositoryUrl || "";
    $("projectDisplayOrder").value = item.display_order ?? item.displayOrder ?? 0;
    $("projectIsFeatured").value = item.is_featured || item.isFeatured ? "1" : "0";
    $("projectIsActive").value = item.is_active === false || item.is_active === 0 ? "0" : "1";

    $("projectFormTitle").textContent = "Edit Project";
    $("projectSubmitButton").textContent = "Save Changes";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function deleteProject(id) {
    if (!confirm("Delete this project?")) return;

    await request(`${API}/${id}`, { method: "DELETE" });
    status("Project deleted.");
    await loadProjects();
  }

  function renderProjects() {
    const list = $("projectsList");

    if (!projects.length) {
      list.innerHTML = '<div class="gland-empty">No projects yet. Create your first project from the form.</div>';
      return;
    }

    list.innerHTML = projects.map((item) => {
      const id = escapeHtml(item.id);
      const title = escapeHtml(item.title || "Untitled Project");
      const category = escapeHtml(item.category || "No category");
      const desc = escapeHtml(item.description || "No description");
      const tech = escapeHtml(item.technologies || "No technologies");

      return `
        <article class="gland-list-card">
          <h3 class="gland-list-card-title">${title}</h3>
          <p class="gland-list-card-meta">${category}</p>
          <p class="gland-list-card-meta">${desc}</p>
          <p class="gland-list-card-meta">${tech}</p>
          <div class="gland-list-card-actions">
            <button type="button" class="gland-btn" data-edit-project="${id}">Edit</button>
            <button type="button" class="gland-btn gland-btn-danger" data-delete-project="${id}">Delete</button>
          </div>
        </article>
      `;
    }).join("");

    document.querySelectorAll("[data-edit-project]").forEach((button) => {
      button.addEventListener("click", () => editProject(button.dataset.editProject));
    });

    document.querySelectorAll("[data-delete-project]").forEach((button) => {
      button.addEventListener("click", () => deleteProject(button.dataset.deleteProject));
    });
  }

  async function loadProjects() {
    status("Loading projects...");
    const payload = await request(API);
    projects = normalize(payload);
    renderProjects();
    status(`Loaded ${projects.length} project(s) from MySQL.`);
  }

  async function saveProject(event) {
    event.preventDefault();

    const id = $("projectId").value;
    const payload = getProjectPayload();

    if (!payload.title) {
      status("Project title is required.");
      return;
    }

    if (id) {
      await request(`${API}/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload)
      });
      status("Project updated.");
    } else {
      await request(API, {
        method: "POST",
        body: JSON.stringify(payload)
      });
      status("Project created.");
    }

    resetForm();
    await loadProjects();
  }

  function boot() {
    $("projectForm").addEventListener("submit", saveProject);
    $("projectResetButton").addEventListener("click", resetForm);

    document.querySelectorAll("[data-refresh-page]").forEach((button) => {
      button.addEventListener("click", loadProjects);
    });

    loadProjects().catch((error) => status(error.message));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();