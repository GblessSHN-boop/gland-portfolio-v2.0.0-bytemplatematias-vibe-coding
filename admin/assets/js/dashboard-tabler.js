(function () {
  "use strict";

  const formatter = new Intl.NumberFormat("en-US");

  function byId(id) {
    return document.getElementById(id);
  }

  function setText(id, value, suffix = "") {
    const target = byId(id);
    if (!target) return;

    if (value === null || value === undefined || value === "") {
      target.textContent = "0" + suffix;
      return;
    }

    const number = Number(value);
    target.textContent = Number.isFinite(number) ? formatter.format(number) + suffix : String(value) + suffix;
  }

  function getFirst(source, keys, fallback = 0) {
    for (const key of keys) {
      if (source && source[key] !== undefined && source[key] !== null) {
        return source[key];
      }
    }
    return fallback;
  }

  function normalizePayload(payload) {
    return payload && (payload.data || payload.summary || payload.result || payload);
  }

  function renderRows(tbodyId, rows, columns, emptyText) {
    const tbody = byId(tbodyId);
    if (!tbody) return;

    if (!Array.isArray(rows) || rows.length === 0) {
      tbody.innerHTML = `<tr><td colspan="${columns.length}" class="gland-empty">${emptyText}</td></tr>`;
      return;
    }

    tbody.innerHTML = rows.slice(0, 8).map((row) => {
      return "<tr>" + columns.map((column) => {
        const value = getFirst(row, column.keys, column.fallback || "—");
        return `<td>${escapeHtml(String(value))}</td>`;
      }).join("") + "</tr>";
    }).join("");
  }

  function escapeHtml(value) {
    return value
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function logout() {
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include"
      });
    } catch (error) {
      // Tetap redirect. Manusia suka tombol logout yang benar-benar logout, mengejutkan.
    }

    window.location.href = "login.html";
  }

  async function loadDashboard() {
    const errorBox = byId("dashboardError");

    try {
      const response = await fetch("/api/analytics/summary", {
        method: "GET",
        credentials: "include",
        headers: {
          "Accept": "application/json"
        }
      });

      if (response.status === 401) {
        window.location.href = "login.html";
        return;
      }

      const payload = await response.json();
      const data = normalizePayload(payload) || {};
      const metrics = data.metrics || data.totals || data;

      setText("statVisits", getFirst(metrics, ["visits", "total_visits", "page_views", "views"]));
      setText("statUnique", getFirst(metrics, ["unique_visitors", "uniqueVisitors", "visitors"]));
      setText("statEvents", getFirst(metrics, ["events", "total_events"]));
      setText("statMessages", getFirst(metrics, ["messages", "total_messages"]));
      setText("statNewMessages", getFirst(metrics, ["new_messages", "unread_messages", "newMessages"]));
      setText("statApproved", getFirst(metrics, ["approved", "approved_messages"]));
      setText("statProjects", getFirst(metrics, ["projects", "total_projects"]));
      setText("statSocialClicks", getFirst(metrics, ["social_clicks", "socialClicks"]));
      setText("statIntroViews", getFirst(metrics, ["intro_views", "introViews"]));

      const avgDuration = getFirst(metrics, ["avg_duration", "avgDuration", "average_duration"], 0);
      setText("statAvgDuration", avgDuration, "s");

      renderRows(
        "topPagesBody",
        data.top_pages || data.topPages || [],
        [
          { keys: ["page", "page_path", "path", "url"], fallback: "—" },
          { keys: ["visits", "count", "total"], fallback: 0 }
        ],
        "No page analytics yet."
      );

      renderRows(
        "topEventsBody",
        data.top_events || data.topEvents || [],
        [
          { keys: ["type", "event_type"], fallback: "—" },
          { keys: ["name", "event_name"], fallback: "—" },
          { keys: ["total", "count", "value"], fallback: 0 }
        ],
        "No events tracked yet."
      );

      if (errorBox) {
        errorBox.classList.remove("is-visible");
      }
    } catch (error) {
      if (errorBox) {
        errorBox.textContent = "Dashboard data could not be loaded. Check server or database.";
        errorBox.classList.add("is-visible");
      }
    }
  }

  function boot() {
    const logoutButton = byId("logoutButton");
    const refreshButton = byId("refreshDashboardButton");

    if (logoutButton) {
      logoutButton.addEventListener("click", logout);
    }

    if (refreshButton) {
      refreshButton.addEventListener("click", loadDashboard);
    }

    loadDashboard();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();