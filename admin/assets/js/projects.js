const state = {
    projects: [],
    editingProjectId: null,
    isLoading: false,
};

const form = document.querySelector("[data-project-form]");
const listElement = document.querySelector("[data-project-list]");
const statusElement = document.querySelector("[data-page-status]");
const refreshButton = document.querySelector("[data-refresh-projects]");
const resetButton = document.querySelector("[data-reset-project-form]");
const submitButton = document.querySelector("[data-submit-project]");

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
        category: formData.get("category"),
        description: formData.get("description"),
        image_path: formData.get("image_path"),
        project_url: formData.get("project_url"),
        repo_url: formData.get("repo_url"),
        technologies: formData.get("technologies"),
        display_order: Number(formData.get("display_order") || 0),
        is_featured: formData.get("is_featured") === "on",
        is_active: formData.get("is_active") === "on",
    };
}

function setFormProject(project) {
    state.editingProjectId = project?.id || null;

    form.elements.title.value = project?.title || "";
    form.elements.category.value = project?.category || "";
    form.elements.description.value = project?.description || "";
    form.elements.image_path.value = project?.image_path || "";
    form.elements.project_url.value = project?.project_url || "";
    form.elements.repo_url.value = project?.repo_url || "";
    form.elements.technologies.value = project?.technologies || "";
    form.elements.display_order.value = project?.display_order ?? 0;
    form.elements.is_featured.checked = project?.is_featured ?? true;
    form.elements.is_active.checked = project?.is_active ?? true;

    submitButton.textContent = state.editingProjectId ? "Update Project" : "Create Project";
}

function renderProjects() {
    if (!listElement) {
        return;
    }

    if (state.isLoading) {
        listElement.innerHTML = `
            <div class="gland-card gland-empty">
                Loading projects from MySQL...
            </div>
        `;
        return;
    }

    if (!state.projects.length) {
        listElement.innerHTML = `
            <div class="gland-card gland-empty">
                No projects yet. Create the first project to populate the portfolio CMS.
            </div>
        `;
        return;
    }

    listElement.innerHTML = state.projects.map((project) => {
        const imagePath = project.image_path || "../assets/img/project/pro3.png";
        const flags = [
            project.is_featured ? "Featured" : "Not Featured",
            project.is_active ? "Active" : "Inactive",
        ];

        return `
            <article class="gland-card gland-project-card" data-project-id="${escapeHtml(project.id)}">
                <img class="gland-project-image" src="${escapeHtml(imagePath)}" alt="${escapeHtml(project.title)}">

                <h3 class="gland-project-title">${escapeHtml(project.title)}</h3>
                <p class="gland-project-meta">
                    ${escapeHtml(project.category || "Uncategorized")} · Order ${escapeHtml(project.display_order)}
                </p>

                <p class="gland-project-description">${escapeHtml(project.description || "No description yet.")}</p>

                <div class="gland-pill-row">
                    ${flags.map((flag) => `<span class="gland-pill">${escapeHtml(flag)}</span>`).join("")}
                </div>

                <div class="gland-actions">
                    <button class="gland-button secondary" data-action="edit">Edit</button>
                    <button class="gland-button danger" data-action="delete">Delete</button>
                </div>
            </article>
        `;
    }).join("");
}

async function loadProjects() {
    state.isLoading = true;
    renderProjects();
    setStatus("Loading projects...");

    try {
        const payload = await apiRequest("/api/projects");
        state.projects = payload.data || [];
        setStatus(`Loaded ${state.projects.length} project(s) from MySQL.`);
    } catch (error) {
        listElement.innerHTML = `
            <div class="gland-card gland-error">
                ${escapeHtml(error.message)}
            </div>
        `;
        setStatus("Failed to load projects.", "error");
    } finally {
        state.isLoading = false;
        renderProjects();
    }
}

async function saveProject(event) {
    event.preventDefault();

    const payload = getFormPayload();

    if (!payload.title.trim()) {
        setStatus("Project title is required.", "error");
        return;
    }

    try {
        if (state.editingProjectId) {
            const response = await apiRequest(`/api/projects/${state.editingProjectId}`, {
                method: "PATCH",
                body: JSON.stringify(payload),
            });

            state.projects = state.projects.map((project) => {
                if (Number(project.id) === Number(state.editingProjectId)) {
                    return response.data;
                }

                return project;
            });

            setStatus(`Project #${state.editingProjectId} updated.`);
        } else {
            const response = await apiRequest("/api/projects", {
                method: "POST",
                body: JSON.stringify(payload),
            });

            state.projects = [response.data, ...state.projects];
            setStatus(`Project #${response.data.id} created.`);
        }

        setFormProject(null);
        renderProjects();
    } catch (error) {
        setStatus(error.message, "error");
    }
}

async function deleteProject(projectId) {
    const isConfirmed = window.confirm(`Delete project #${projectId}?`);

    if (!isConfirmed) {
        return;
    }

    try {
        await apiRequest(`/api/projects/${projectId}`, {
            method: "DELETE",
        });

        state.projects = state.projects.filter((project) => Number(project.id) !== Number(projectId));
        renderProjects();
        setStatus(`Project #${projectId} deleted.`);
    } catch (error) {
        setStatus(error.message, "error");
    }
}

listElement?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");

    if (!button) {
        return;
    }

    const card = button.closest("[data-project-id]");
    const projectId = Number(card?.dataset.projectId);
    const action = button.dataset.action;
    const project = state.projects.find((item) => Number(item.id) === projectId);

    if (!project) {
        return;
    }

    if (action === "edit") {
        setFormProject(project);
        window.scrollTo(0, 0);
        return;
    }

    if (action === "delete") {
        deleteProject(projectId);
    }
});

form?.addEventListener("submit", saveProject);

resetButton?.addEventListener("click", () => {
    setFormProject(null);
    setStatus("Project form reset.");
});

refreshButton?.addEventListener("click", () => {
    loadProjects();
});

loadProjects();