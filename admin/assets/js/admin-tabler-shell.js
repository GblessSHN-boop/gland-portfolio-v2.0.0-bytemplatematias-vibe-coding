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
      const text = String(element.textContent || "").trim().toLowerCase();
      const isLogoutText = text === "logout";
      const isOurLogout = element.hasAttribute("data-admin-logout");
      const isInsideSidebarFooter = Boolean(element.closest(".gland-sidebar-footer"));

      if (isLogoutText && !isOurLogout && !isInsideSidebarFooter) {
        element.remove();
      }
    });
  }

  function boot() {
    syncActiveNav();
    bindLogout();
    removeLegacyLogoutButtons();

    window.setTimeout(removeLegacyLogoutButtons, 100);
    window.setTimeout(removeLegacyLogoutButtons, 500);
    window.setTimeout(removeLegacyLogoutButtons, 1200);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();