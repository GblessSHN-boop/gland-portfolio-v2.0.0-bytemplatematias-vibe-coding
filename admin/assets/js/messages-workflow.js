(function () {
  "use strict";

  const REFRESH_INTERVAL_MS = 3000;
  let nextRefreshAt = Date.now() + REFRESH_INTERVAL_MS;
  let toastTimer = null;

  const ACTION_HINTS = {
    "mark read": "Tandai pesan sudah dibaca.",
    "approve": "Lead valid dan perlu ditindaklanjuti.",
    "reject": "Pesan tidak cocok atau tidak valid.",
    "archive": "Pesan selesai, simpan sebagai arsip.",
    "delete": "Hapus permanen khusus spam."
  };

  function textOf(element) {
    return String(element && element.textContent ? element.textContent : "").trim();
  }

  function isMessagesPage() {
    return location.pathname.toLowerCase().includes("/admin/messages");
  }

  function findRefreshButton() {
    return Array.from(document.querySelectorAll("button, a"))
      .find((element) => textOf(element).toLowerCase() === "refresh");
  }

  function findLoadedCounter() {
    return Array.from(document.querySelectorAll("main *, .admin-main *, body *"))
      .find((element) => /^Loaded\s+\d+\s+message\(s\)\s+from\s+MySQL\./i.test(textOf(element)));
  }

  function getMessageCount() {
    const counter = findLoadedCounter();
    const match = textOf(counter).match(/Loaded\s+(\d+)\s+message/i);
    return match ? Number(match[1]) : null;
  }

  function isUserEditing() {
    const active = document.activeElement;
    if (!active) return false;

    const tag = active.tagName ? active.tagName.toLowerCase() : "";
    return tag === "input" || tag === "textarea" || tag === "select" || active.isContentEditable;
  }

  function ensureWorkflowPanel() {
    if (document.querySelector("[data-gland-messages-workflow]")) return;

    const counter = findLoadedCounter();
    const host = counter && counter.parentElement ? counter.parentElement : document.querySelector("main") || document.body;

    const panel = document.createElement("section");
    panel.className = "gland-messages-workflow";
    panel.setAttribute("data-gland-messages-workflow", "true");

    panel.innerHTML = `
      <div class="gland-messages-workflow__top">
        <div>
          <p class="gland-messages-workflow__eyebrow">Inbox workflow</p>
          <h2 class="gland-messages-workflow__title">New → Read → Approve / Reject → Archive</h2>
          <p class="gland-messages-workflow__desc">Workflow ringkas untuk memproses pesan contact.</p>
        </div>
        <div class="gland-messages-workflow__refresh">
          Auto refresh: <strong>ON</strong>
          <small data-gland-refresh-status>Setiap 3 detik</small>
        </div>
      </div>
      <div class="gland-messages-workflow__steps">
        <div class="gland-messages-workflow__step"><span>NEW</span><small>Baru masuk.</small></div>
        <div class="gland-messages-workflow__step"><span>READ</span><small>Sudah dibaca.</small></div>
        <div class="gland-messages-workflow__step"><span>APPROVED</span><small>Layak diproses.</small></div>
        <div class="gland-messages-workflow__step"><span>REJECTED</span><small>Tidak cocok.</small></div>
        <div class="gland-messages-workflow__step"><span>ARCHIVED</span><small>Selesai.</small></div>
        <div class="gland-messages-workflow__step"><span>DELETE</span><small>Spam.</small></div>
      </div>
    `;

    if (counter) {
      counter.insertAdjacentElement("beforebegin", panel);
    } else {
      host.insertAdjacentElement("afterbegin", panel);
    }
  }

  function ensureToast() {
    let toast = document.querySelector("[data-gland-messages-toast]");
    if (toast) return toast;

    toast = document.createElement("div");
    toast.className = "gland-messages-toast";
    toast.setAttribute("data-gland-messages-toast", "true");
    toast.setAttribute("role", "status");
    toast.setAttribute("aria-live", "polite");
    document.body.appendChild(toast);

    return toast;
  }

  function showToast(message) {
    const toast = ensureToast();
    toast.textContent = message;
    toast.classList.add("is-visible");

    clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      toast.classList.remove("is-visible");
    }, 3200);
  }

  function normalizeAction(text) {
    const lower = text.toLowerCase();

    if (lower.includes("mark read")) return "mark read";
    if (lower.includes("approve")) return "approve";
    if (lower.includes("reject")) return "reject";
    if (lower.includes("archive")) return "archive";
    if (lower.includes("delete")) return "delete";

    return "";
  }

  function findActionCard(button) {
    let current = button.parentElement;

    while (current && current !== document.body) {
      const actionButtons = Array.from(current.querySelectorAll("button")).filter((item) => normalizeAction(textOf(item)));

      if (actionButtons.length >= 3) {
        return current;
      }

      current = current.parentElement;
    }

    return null;
  }

  function enhanceCards() {
    const actionButtons = Array.from(document.querySelectorAll("button")).filter((button) => normalizeAction(textOf(button)));

    actionButtons.forEach((button) => {
      const action = normalizeAction(textOf(button));
      button.dataset.glandAction = action.replace(/\s+/g, "-");
      button.setAttribute("title", ACTION_HINTS[action] || "Message action");

      const card = findActionCard(button);
      if (card) {
        card.classList.add("gland-message-card");
      }
    });
  }

  function updateRefreshStatus() {
    const status = document.querySelector("[data-gland-refresh-status]");
    if (!status) return;

    if (isUserEditing()) {
      status.textContent = "Pause saat admin mengetik.";
      return;
    }

    const seconds = Math.max(0, Math.ceil((nextRefreshAt - Date.now()) / 1000));
    status.textContent = `Refresh dalam ${seconds} detik.`;
  }

  function performRefresh() {
    const button = findRefreshButton();

    if (!button || isUserEditing() || document.hidden) {
      return;
    }

    const before = getMessageCount();

    button.click();
    nextRefreshAt = Date.now() + REFRESH_INTERVAL_MS;

    window.setTimeout(() => {
      const after = getMessageCount();

      if (typeof before === "number" && typeof after === "number" && after > before) {
        showToast(`${after - before} pesan baru masuk.`);
        const firstCard = document.querySelector(".gland-message-card");

        if (firstCard) {
          firstCard.classList.add("gland-new-message-pulse");
          window.setTimeout(() => firstCard.classList.remove("gland-new-message-pulse"), 2400);
        }
      }

      ensureWorkflowPanel();
      enhanceCards();
      updateRefreshStatus();
    }, 700);
  }

  function boot() {
    if (!isMessagesPage()) return;

    document.body.classList.add("gland-messages-enhanced");

    ensureWorkflowPanel();
    enhanceCards();

    window.setInterval(() => {
      updateRefreshStatus();

      if (Date.now() >= nextRefreshAt) {
        performRefresh();
      }
    }, 1000);

    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) {
        nextRefreshAt = Date.now() + 500;
        performRefresh();
      }
    });

    window.addEventListener("focus", () => {
      nextRefreshAt = Date.now() + 500;
      performRefresh();
    });

    const observer = new MutationObserver(() => {
      ensureWorkflowPanel();
      enhanceCards();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();