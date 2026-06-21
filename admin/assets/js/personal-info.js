const state = {
    personalInfo: null,
    isLoading: false,
};

const form = document.querySelector("[data-personal-info-form]");
const statusElement = document.querySelector("[data-page-status]");
const refreshButton = document.querySelector("[data-refresh-personal-info]");
const resetButton = document.querySelector("[data-reset-personal-info]");
const previewImage = document.querySelector("[data-preview-photo]");
const previewName = document.querySelector("[data-preview-name]");
const previewRole = document.querySelector("[data-preview-role]");
const previewDescription = document.querySelector("[data-preview-description]");
const previewEmail = document.querySelector("[data-preview-email]");
const previewPhone = document.querySelector("[data-preview-phone]");
const previewAddress = document.querySelector("[data-preview-address]");

function setStatus(message, type = "info") {
    if (!statusElement) {
        return;
    }

    statusElement.textContent = message || "";
    statusElement.dataset.type = type;
}

function resolveImagePath(path) {
    if (!path) {
        return "../assets/img/about/gland-personal-info.png";
    }

    if (path.startsWith("assets/")) {
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

function getFormPayload() {
    const formData = new FormData(form);

    return {
        full_name: formData.get("full_name"),
        role_title: formData.get("role_title"),
        description: formData.get("description"),
        email: formData.get("email"),
        phone: formData.get("phone"),
        address: formData.get("address"),
        photo_path: formData.get("photo_path"),
        resume_url: formData.get("resume_url"),
        is_active: formData.get("is_active") === "on",
    };
}

function setFormPersonalInfo(info) {
    form.elements.full_name.value = info?.full_name || "";
    form.elements.role_title.value = info?.role_title || "";
    form.elements.description.value = info?.description || "";
    form.elements.email.value = info?.email || "";
    form.elements.phone.value = info?.phone || "";
    form.elements.address.value = info?.address || "";
    form.elements.photo_path.value = info?.photo_path || "";
    form.elements.resume_url.value = info?.resume_url || "";
    form.elements.is_active.checked = info?.is_active ?? true;

    renderPreview();
}

function renderPreview() {
    const payload = getFormPayload();

    previewImage.src = resolveImagePath(payload.photo_path);
    previewName.textContent = payload.full_name || "Full name";
    previewRole.textContent = payload.role_title || "Role title";
    previewDescription.textContent = payload.description || "Personal description preview.";
    previewEmail.textContent = payload.email || "email@example.com";
    previewPhone.textContent = payload.phone || "Phone number";
    previewAddress.textContent = payload.address || "Address";
}

async function loadPersonalInfo() {
    state.isLoading = true;
    setStatus("Loading personal info...");

    try {
        const payload = await apiRequest("/api/personal-info");
        state.personalInfo = payload.data;
        setFormPersonalInfo(state.personalInfo);
        setStatus("Personal info loaded from MySQL.");
    } catch (error) {
        setStatus(error.message, "error");
    } finally {
        state.isLoading = false;
    }
}

async function savePersonalInfo(event) {
    event.preventDefault();

    const payload = getFormPayload();

    if (!payload.full_name.trim()) {
        setStatus("Full name is required.", "error");
        return;
    }

    try {
        const response = await apiRequest("/api/personal-info", {
            method: "PATCH",
            body: JSON.stringify(payload),
        });

        state.personalInfo = response.data;
        setFormPersonalInfo(state.personalInfo);
        setStatus("Personal info updated.");
    } catch (error) {
        setStatus(error.message, "error");
    }
}

form?.addEventListener("submit", savePersonalInfo);

form?.addEventListener("input", () => {
    renderPreview();
});

refreshButton?.addEventListener("click", () => {
    loadPersonalInfo();
});

resetButton?.addEventListener("click", () => {
    setFormPersonalInfo(state.personalInfo);
    setStatus("Form reset to saved data.");
});

loadPersonalInfo();