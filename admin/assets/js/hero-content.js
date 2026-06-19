const state = {
    heroContent: null,
};

const form = document.querySelector("[data-hero-content-form]");
const statusElement = document.querySelector("[data-page-status]");
const refreshButton = document.querySelector("[data-refresh-hero-content]");
const resetButton = document.querySelector("[data-reset-hero-content]");

const previewEyebrow = document.querySelector("[data-preview-eyebrow]");
const previewTitleLine1 = document.querySelector("[data-preview-title-line-1]");
const previewTitleLine2 = document.querySelector("[data-preview-title-line-2]");
const previewDescription = document.querySelector("[data-preview-description]");
const previewAvailability = document.querySelector("[data-preview-availability]");
const previewLocation = document.querySelector("[data-preview-location]");
const previewPhone = document.querySelector("[data-preview-phone]");
const previewIntro = document.querySelector("[data-preview-intro]");
const previewMediaSlot = document.querySelector("[data-preview-media-slot]");

function setStatus(message, type = "info") {
    if (!statusElement) {
        return;
    }

    statusElement.textContent = message || "";
    statusElement.dataset.type = type;
}

function escapeAttribute(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll('"', "&quot;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
}

function resolveAssetPath(path) {
    if (!path) {
        return "../assets/video/hero-right-iklan-4k.mp4";
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
        eyebrow: formData.get("eyebrow"),
        title_line_1: formData.get("title_line_1"),
        title_line_2: formData.get("title_line_2"),
        description: formData.get("description"),
        availability_text: formData.get("availability_text"),
        availability_location: formData.get("availability_location"),
        phone_label: formData.get("phone_label"),
        phone_url: formData.get("phone_url"),
        intro_video_label: formData.get("intro_video_label"),
        intro_video_url: formData.get("intro_video_url"),
        hero_media_type: formData.get("hero_media_type"),
        hero_media_path: formData.get("hero_media_path"),
        background_image_path: formData.get("background_image_path"),
        is_active: formData.get("is_active") === "on",
    };
}

function setFormHeroContent(info) {
    form.elements.eyebrow.value = info?.eyebrow || "";
    form.elements.title_line_1.value = info?.title_line_1 || "";
    form.elements.title_line_2.value = info?.title_line_2 || "";
    form.elements.description.value = info?.description || "";
    form.elements.availability_text.value = info?.availability_text || "";
    form.elements.availability_location.value = info?.availability_location || "";
    form.elements.phone_label.value = info?.phone_label || "";
    form.elements.phone_url.value = info?.phone_url || "";
    form.elements.intro_video_label.value = info?.intro_video_label || "";
    form.elements.intro_video_url.value = info?.intro_video_url || "";
    form.elements.hero_media_type.value = info?.hero_media_type || "video";
    form.elements.hero_media_path.value = info?.hero_media_path || "";
    form.elements.background_image_path.value = info?.background_image_path || "";
    form.elements.is_active.checked = info?.is_active ?? true;

    renderPreview();
}

function renderPreview() {
    const payload = getFormPayload();

    previewEyebrow.textContent = payload.eyebrow || "Hero eyebrow";
    previewTitleLine1.textContent = payload.title_line_1 || "AI Engineer";
    previewTitleLine2.textContent = payload.title_line_2 || "Creative Designer";
    previewDescription.textContent = payload.description || "Hero description preview.";
    previewAvailability.textContent = payload.availability_text || "Availability text";
    previewLocation.textContent = payload.availability_location || "Location";
    previewPhone.textContent = payload.phone_label || "Phone";
    previewIntro.textContent = payload.intro_video_label || "Intro Video";

    const mediaPath = escapeAttribute(resolveAssetPath(payload.hero_media_path));

    if (payload.hero_media_type === "image") {
        previewMediaSlot.innerHTML = `
            <img class="gland-hero-media-preview" src="${mediaPath}" alt="Hero media preview">
        `;
        return;
    }

    previewMediaSlot.innerHTML = `
        <video class="gland-hero-media-preview" src="${mediaPath}" muted autoplay loop playsinline></video>
    `;
}

async function loadHeroContent() {
    setStatus("Loading hero content...");

    try {
        const payload = await apiRequest("/api/hero-content");
        state.heroContent = payload.data;
        setFormHeroContent(state.heroContent);
        setStatus("Hero content loaded from MySQL.");
    } catch (error) {
        setStatus(error.message, "error");
    }
}

async function saveHeroContent(event) {
    event.preventDefault();

    const payload = getFormPayload();

    if (!payload.title_line_1.trim()) {
        setStatus("Hero title line 1 is required.", "error");
        return;
    }

    try {
        const response = await apiRequest("/api/hero-content", {
            method: "PATCH",
            body: JSON.stringify(payload),
        });

        state.heroContent = response.data;
        setFormHeroContent(state.heroContent);
        setStatus("Hero content updated.");
    } catch (error) {
        setStatus(error.message, "error");
    }
}

form?.addEventListener("submit", saveHeroContent);

form?.addEventListener("input", () => {
    renderPreview();
});

refreshButton?.addEventListener("click", () => {
    loadHeroContent();
});

resetButton?.addEventListener("click", () => {
    setFormHeroContent(state.heroContent);
    setStatus("Form reset to saved hero data.");
});

loadHeroContent();