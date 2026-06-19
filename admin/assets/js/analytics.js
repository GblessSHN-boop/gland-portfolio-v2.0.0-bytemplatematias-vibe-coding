const statusElement = document.querySelector("[data-page-status]");
const eventsElement = document.querySelector("[data-events-list]");
const form = document.querySelector("[data-analytics-event-form]");
const refreshButton = document.querySelector("[data-refresh-analytics]");

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

function getVisitorId() {
    let visitorId = localStorage.getItem("gland_admin_test_visitor_id");

    if (!visitorId) {
        visitorId = `admin-test-${Date.now()}-${Math.random().toString(16).slice(2)}`;
        localStorage.setItem("gland_admin_test_visitor_id", visitorId);
    }

    return visitorId;
}

function getSessionId() {
    let sessionId = sessionStorage.getItem("gland_admin_test_session_id");

    if (!sessionId) {
        sessionId = `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
        sessionStorage.setItem("gland_admin_test_session_id", sessionId);
    }

    return sessionId;
}

async function apiRequest(path, options = {}) {
    const response = await fetch(path, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
        ...options,
    });

    const payload = await response.json();

    if (!response.ok || payload.success === false) {
        throw new Error(payload.message || "Request failed.");
    }

    return payload;
}

function renderEvents(events) {
    if (!events.length) {
        eventsElement.innerHTML = `
            <div class="gland-card gland-empty">
                No analytics events yet.
            </div>
        `;
        return;
    }

    eventsElement.innerHTML = `
        <div class="gland-card gland-table-wrap">
            <table class="gland-data-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Type</th>
                        <th>Name</th>
                        <th>Page</th>
                        <th>Target</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody>
                    ${events.map((event) => `
                        <tr>
                            <td>${escapeHtml(event.id)}</td>
                            <td>${escapeHtml(event.event_type)}</td>
                            <td>${escapeHtml(event.event_name)}</td>
                            <td>${escapeHtml(event.page_path)}</td>
                            <td>${escapeHtml(event.target_url || "-")}</td>
                            <td>${escapeHtml(event.created_at || "-")}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;
}

async function loadEvents() {
    setStatus("Loading analytics events...");

    try {
        const payload = await apiRequest("/api/analytics/events");
        renderEvents(payload.data || []);
        setStatus(`Loaded ${(payload.data || []).length} analytics event(s).`);
    } catch (error) {
        setStatus(error.message, "error");
    }
}

async function submitEvent(event) {
    event.preventDefault();

    const formData = new FormData(form);

    try {
        await apiRequest("/api/analytics/event", {
            method: "POST",
            body: JSON.stringify({
                visitor_id: getVisitorId(),
                session_id: getSessionId(),
                event_type: formData.get("event_type"),
                event_name: formData.get("event_name"),
                event_value: formData.get("event_value"),
                page_path: formData.get("page_path"),
                target_url: formData.get("target_url"),
                metadata: {
                    source: "admin-analytics-test",
                },
            }),
        });

        setStatus("Test analytics event recorded.");
        await loadEvents();
    } catch (error) {
        setStatus(error.message, "error");
    }
}

form?.addEventListener("submit", submitEvent);
refreshButton?.addEventListener("click", loadEvents);

loadEvents();