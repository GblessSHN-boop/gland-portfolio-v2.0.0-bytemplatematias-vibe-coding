const state = {
    siteIdentity: null,
};

const form = document.querySelector("[data-site-identity-form]");
const statusElement = document.querySelector("[data-page-status]");
const refreshButton = document.querySelector("[data-refresh-site-identity]");
const resetButton = document.querySelector("[data-reset-site-identity]");

const previewLogo = document.querySelector("[data-preview-logo]");
const previewTitle = document.querySelector("[data-preview-title]");
const previewDescription = document.querySelector("[data-preview-description]");
const previewCanonical = document.querySelector("[data-preview-canonical]");
const previewPreloader = document.querySelector("[data-preview-preloader]");
const previewSocials = document.querySelector("[data-preview-socials]");

function setStatus(message, type = "info") {
    if (!statusElement) {
        return;
    }

    statusElement.textContent = message || "";
    statusElement.dataset.type = type;
}

function resolveAssetPath(path) {
    if (!path) {
        return "../assets/img/logo/gland-header-icon.gif";
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
        site_title: formData.get("site_title"),
        meta_description: formData.get("meta_description"),
        canonical_url: formData.get("canonical_url"),
        logo_path: formData.get("logo_path"),
        header_icon_path: formData.get("header_icon_path"),
        favicon_path: formData.get("favicon_path"),
        preloader_text: formData.get("preloader_text"),
        youtube_url: formData.get("youtube_url"),
        github_url: formData.get("github_url"),
        instagram_url: formData.get("instagram_url"),
        linkedin_url: formData.get("linkedin_url"),
        is_active: formData.get("is_active") === "on",
    };
}

function setFormSiteIdentity(info) {
    form.elements.site_title.value = info?.site_title || "";
    form.elements.meta_description.value = info?.meta_description || "";
    form.elements.canonical_url.value = info?.canonical_url || "";
    form.elements.logo_path.value = info?.logo_path || "";
    form.elements.header_icon_path.value = info?.header_icon_path || "";
    form.elements.favicon_path.value = info?.favicon_path || "";
    form.elements.preloader_text.value = info?.preloader_text || "";
    form.elements.youtube_url.value = info?.youtube_url || "";
    form.elements.github_url.value = info?.github_url || "";
    form.elements.instagram_url.value = info?.instagram_url || "";
    form.elements.linkedin_url.value = info?.linkedin_url || "";
    form.elements.is_active.checked = info?.is_active ?? true;

    renderPreview();
}

function renderPreview() {
    const payload = getFormPayload();

    previewLogo.src = resolveAssetPath(payload.header_icon_path || payload.logo_path);
    previewTitle.textContent = payload.site_title || "Site title";
    previewDescription.textContent = payload.meta_description || "Meta description preview.";
    previewCanonical.textContent = payload.canonical_url || "Canonical URL";
    previewPreloader.textContent = `Preloader: ${payload.preloader_text || "GLAND"}`;

    previewSocials.innerHTML = [
        ["YouTube", payload.youtube_url],
        ["GitHub", payload.github_url],
        ["Instagram", payload.instagram_url],
        ["LinkedIn", payload.linkedin_url],
    ].map(([label, value]) => `<span>${label}: ${value || "-"}</span>`).join("");
}

async function loadSiteIdentity() {
    setStatus("Loading site identity...");

    try {
        const payload = await apiRequest("/api/site-identity");
        state.siteIdentity = payload.data;
        setFormSiteIdentity(state.siteIdentity);
        setStatus("Site identity loaded from MySQL.");
    } catch (error) {
        setStatus(error.message, "error");
    }
}

async function saveSiteIdentity(event) {
    event.preventDefault();

    const payload = getFormPayload();

    if (!payload.site_title.trim()) {
        setStatus("Site title is required.", "error");
        return;
    }

    try {
        const response = await apiRequest("/api/site-identity", {
            method: "PATCH",
            body: JSON.stringify(payload),
        });

        state.siteIdentity = response.data;
        setFormSiteIdentity(state.siteIdentity);
        setStatus("Site identity updated.");
    } catch (error) {
        setStatus(error.message, "error");
    }
}

form?.addEventListener("submit", saveSiteIdentity);

form?.addEventListener("input", () => {
    renderPreview();
});

refreshButton?.addEventListener("click", () => {
    loadSiteIdentity();
});

resetButton?.addEventListener("click", () => {
    setFormSiteIdentity(state.siteIdentity);
    setStatus("Form reset to saved site identity data.");
});

loadSiteIdentity();