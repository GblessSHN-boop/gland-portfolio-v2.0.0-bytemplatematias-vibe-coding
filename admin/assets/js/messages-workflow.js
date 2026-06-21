(function () {
  "use strict";

  const REFRESH_INTERVAL_MS = 5000;
  const ACTION_LABELS = {
    "mark read": "Tandai pesan sudah dibaca. Cocok untuk pesan baru yang sudah kamu cek.",
    "approve": "Setujui lead/pesan yang layak ditindaklanjuti.",
    "reject": "Tolak pesan yang tidak cocok, tidak valid, atau bukan prioritas.",
    "archive": "Arsipkan pesan yang sudah selesai diproses.",
    "delete": "Hapus permanen. Pakai hanya untuk spam/sampah."
  };

  let lastCount = null;
  let nextRefreshAt = Date.now() + REFRESH_INTERVAL_MS;
  let toastTimer = null;

  function textOf(element) {
    return String(element && element.textContent ? element.textContent : "").trim();
  }

  function isMessagesPage() {
    return location.pathname.toLowerCase().includes("/admin/messages");
  }

  function findRefreshButton() {
    const controls = Array.from(document.querySelectorAll("button, a"));
    return controls.find((element) => textOf(element).toLowerCase() === "refresh");
  }

  function findLoadedCounter() {
    const candidates = Array.from(document.querySelectorAll("main *, .admin-main *, body *"));

    return candidates.find((element) => {
      const text = textOf(element);
      return /^Loaded\s+\d+\s+message\(s\)\s+from\s+MySQL\./i.test(text);
    });
  }

  function getMessageCount() {
    const counter = findLoadedCounter();
    const text = textOf(counter);
    const match = text.match(/Loaded\s+(\d+)\s+message/i);

    if (!match) {
      return null;
    }

    return Number(match[1]);
  }

  function isUserEditing() {
    const active = document.activeElement;

    if (!active) {
      return false;
    }

    const tag = active.tagName ? active.tagName.toLowerCase() : "";

    return tag === "input" || tag === "textarea" || tag === "select" || active.isContentEditable;
  }

  function ensureWorkflowPanel() {
    if (document.querySelector("[data-gland-messages-workflow]")) {
      return;
    }

    const counter = findLoadedCounter();
    const host = counter && counter.parentElement ? counter.parentElement : document.querySelector("main") || document.body;

    const panel = document.createElement("section");
    panel.className = "gland-messages-workflow";
    panel.setAttribute("data-gland-messages-workflow", "true");

    panel.innerHTML = `
      <div class="gland-messages-workflow__top">
        <div>
          <p class="gland-messages-workflow__eyebrow">Message workflow</p>
          <h2 class="gland-messages-workflow__title">Alur inbox admin yang jelas</h2>
          <p class="gland-messages-workflow__desc">
            Setiap pesan masuk otomatis refresh cepat. Gunakan status secara berurutan:
            baca dulu, tentukan apakah layak ditindaklanjuti, lalu arsipkan ketika selesai.
            Delete hanya untuk spam, bukan untuk pesan normal yang sudah selesai.
          </p>
        </div>
        <div class="gland-messages-workflow__refresh">
          Auto refresh: <strong>ON</strong><br>
          <small data-gland-refresh-status>Setiap 5 detik</small>
        </div>
      </div>
      <div class="gland-messages-workflow__steps">
        <div class="gland-messages-workflow__step"><span>NEW</span><small>Pesan baru masuk dan belum dicek.</small></div>
        <div class="gland-messages-workflow__step"><span>READ</span><small>Admin sudah membaca isi pesan.</small></div>
        <div class="gland-messages-workflow__step"><span>APPROVED</span><small>Lead layak diproses atau dibalas.</small></div>
        <div class="gland-messages-workflow__step"><span>REJECTED</span><small>Pesan tidak valid atau tidak cocok.</small></div>
        <div class="gland-messages-workflow__step"><span>ARCHIVED</span><small>Pesan selesai dan disimpan.</small></div>
        <div class="gland-messages-workflow__step"><span>DELETE</span><small>Hapus permanen khusus spam.</small></div>
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

    if (toast) {
      return toast;
    }

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
    toastTimer = setTimeout(() => {
      toast.classList.remove("is-visible");
    }, 4200);
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
      button.setAttribute("title", ACTION_LABELS[action] || "Admin message action");

      const card = findActionCard(button);

      if (!card) {
        return;
      }

      card.classList.add("gland-message-card");

      if (!card.querySelector("[data-gland-message-hint]")) {
        const hint = document.createElement("div");
        hint.className = "gland-message-card__hint";
        hint.setAttribute("data-gland-message-hint", "true");
        hint.textContent = "Alur kerja: Mark Read setelah dibaca, Approve kalau perlu ditindaklanjuti, Reject kalau tidak cocok, Archive kalau selesai. Delete hanya untuk spam.";
        card.appendChild(hint);
      }
    });
  }

  function updateRefreshStatus() {
    const target = document.querySelector("[data-gland-refresh-status]");

    if (!target) {
      return;
    }

    if (isUserEditing()) {
      target.textContent = "Pause sebentar karena admin sedang mengetik.";
      return;
    }

    const seconds = Math.max(0, Math.ceil((nextRefreshAt - Date.now()) / 1000));
    target.textContent = `Refresh berikutnya dalam ${seconds} detik.`;
  }

  function performRefresh(reason) {
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
        showToast(`Ada ${after - before} pesan baru masuk.`);
        const firstCard = document.querySelector(".gland-message-card");
        if (firstCard) {
          firstCard.classList.add("gland-new-message-pulse");
          window.setTimeout(() => firstCard.classList.remove("gland-new-message-pulse"), 3200);
        }
      }

      lastCount = after;
      enhanceCards();
      updateRefreshStatus();
    }, 900);
  }

  function boot() {
    if (!isMessagesPage()) {
      return;
    }

    document.body.classList.add("gland-messages-enhanced");

    ensureWorkflowPanel();
    enhanceCards();

    lastCount = getMessageCount();

    window.setInterval(() => {
      updateRefreshStatus();

      if (Date.now() >= nextRefreshAt) {
        performRefresh("interval");
      }
    }, 1000);

    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) {
        nextRefreshAt = Date.now() + 1000;
        performRefresh("visibility");
      }
    });

    window.addEventListener("focus", () => {
      nextRefreshAt = Date.now() + 1000;
      performRefresh("focus");
    });

    const observer = new MutationObserver(() => {
      ensureWorkflowPanel();
      enhanceCards();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    showToast("Messages auto-refresh aktif.");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();