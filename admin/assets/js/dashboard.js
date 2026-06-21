const statusElement = document.querySelector("[data-page-status]");
const cardsElement = document.querySelector("[data-dashboard-cards]");
const topPagesElement = document.querySelector("[data-top-pages]");
const topEventsElement = document.querySelector("[data-top-events]");
const refreshButton = document.querySelector("[data-refresh-dashboard]");

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

async function apiRequest(path) {
    const response = await fetch(path);
    const payload = await response.json();

    if (!response.ok || payload.success === false) {
        throw new Error(payload.message || "Request failed.");
    }

    return payload;
}

function renderCards(totals) {
    const cards = [
        ["Visits", totals.visits],
        ["Unique Visitors", totals.unique_visitors],
        ["Events", totals.events],
        ["Messages", totals.messages],
        ["New Messages", totals.new_messages],
        ["Approved", totals.approved_messages],
        ["Projects", totals.projects],
        ["Media Files", totals.media_files],
        ["Social Clicks", totals.social_clicks],
        ["Intro Views", totals.intro_video_views],
        ["Avg Duration", `${totals.avg_duration_seconds}s`],
    ];

    cardsElement.innerHTML = cards.map(([label, value]) => `
        <article class="gland-card gland-stat-card">
            <p class="gland-stat-label">${escapeHtml(label)}</p>
            <h3 class="gland-stat-value">${escapeHtml(value ?? 0)}</h3>
        </article>
    `).join("");
}

function renderTable(element, headers, rows, rowRenderer) {
    if (!rows.length) {
        element.innerHTML = `
            <div class="gland-card gland-empty">
                No data yet.
            </div>
        `;
        return;
    }

    element.innerHTML = `
        <div class="gland-card gland-table-wrap">
            <table class="gland-data-table">
                <thead>
                    <tr>
                        ${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}
                    </tr>
                </thead>
                <tbody>
                    ${rows.map(rowRenderer).join("")}
                </tbody>
            </table>
        </div>
    `;
}

async function loadDashboard() {
    setStatus("Loading dashboard summary...");

    try {
        const payload = await apiRequest("/api/analytics/summary");
        const data = payload.data;

        renderCards(data.totals || {});

        renderTable(
            topPagesElement,
            ["Page", "Visits"],
            data.top_pages || [],
            (row) => `
                <tr>
                    <td>${escapeHtml(row.page_path || "/")}</td>
                    <td>${escapeHtml(row.total || 0)}</td>
                </tr>
            `
        );

        renderTable(
            topEventsElement,
            ["Type", "Name", "Total"],
            data.top_events || [],
            (row) => `
                <tr>
                    <td>${escapeHtml(row.event_type || "-")}</td>
                    <td>${escapeHtml(row.event_name || "-")}</td>
                    <td>${escapeHtml(row.total || 0)}</td>
                </tr>
            `
        );

        setStatus("Dashboard summary loaded.");
    } catch (error) {
        setStatus(error.message, "error");
    }
}

refreshButton?.addEventListener("click", loadDashboard);

loadDashboard();