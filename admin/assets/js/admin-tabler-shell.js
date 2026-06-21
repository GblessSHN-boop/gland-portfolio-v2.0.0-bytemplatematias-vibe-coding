(function () {
  "use strict";

  const current = (location.pathname.split("/").pop() || "").toLowerCase();

  function syncActiveNav() {
    document.querySelectorAll("[data-admin-nav]").forEach((link) => {
      const href = (link.getAttribute("href") || "").split("/").pop().toLowerCase();
      link.classList.toggle("is-active", href === current);
    });
  }

  function bindLogout() {
    document.querySelectorAll("[data-admin-logout]").forEach((button) => {
      if (button.dataset.boundLogout === "true") return;

      button.dataset.boundLogout = "true";
      button.addEventListener("click", async () => {
        try {
          await fetch("/api/auth/logout", {
            method: "POST",
            credentials: "include"
          });
        } catch (error) {}

        window.location.href = "login.html";
      });
    });
  }

  function removeLegacyLogoutButtons() {
    document.querySelectorAll("button, a").forEach((element) => {
      const label = String(element.textContent || "").trim().toLowerCase();
      const isLegacyLogout = label === "logout";
      const isOfficialLogout = element.hasAttribute("data-admin-logout") || Boolean(element.closest(".gland-sidebar-footer"));

      if (isLegacyLogout && !isOfficialLogout) {
        element.remove();
      }
    });

    document.querySelectorAll("#logoutButton").forEach((element) => {
      const isOfficialLogout = element.hasAttribute("data-admin-logout") || Boolean(element.closest(".gland-sidebar-footer"));
      if (!isOfficialLogout) {
        element.remove();
      }
    });
  }

  function boot() {
    syncActiveNav();
    bindLogout();
    removeLegacyLogoutButtons();

    const observer = new MutationObserver(() => {
      removeLegacyLogoutButtons();
      syncActiveNav();
      bindLogout();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    window.setInterval(removeLegacyLogoutButtons, 750);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();


/* GLAND COMPACT SIDEBAR ACTIVE START */
(function () {
  "use strict";

  function normalizePage(value) {
    return String(value || "")
      .split("?")[0]
      .split("#")[0]
      .split("/")
      .filter(Boolean)
      .pop() || "dashboard.html";
  }

  function markActiveSidebarLink() {
    const currentPage = normalizePage(window.location.pathname);
    const links = document.querySelectorAll("[data-admin-nav]");

    links.forEach((link) => {
      const hrefPage = normalizePage(link.getAttribute("href"));
      const isActive = hrefPage === currentPage;

      link.classList.toggle("is-active", isActive);
      link.classList.toggle("active", isActive);

      if (isActive) {
        link.setAttribute("aria-current", "page");
      } else {
        link.removeAttribute("aria-current");
      }
    });

    const activeLink = document.querySelector("[data-admin-nav].is-active");
    if (activeLink && activeLink.scrollIntoView) {
      activeLink.scrollIntoView({ block: "nearest", inline: "nearest" });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", markActiveSidebarLink);
  } else {
    markActiveSidebarLink();
  }

  window.addEventListener("pageshow", markActiveSidebarLink);
})();
/* GLAND COMPACT SIDEBAR ACTIVE END */
