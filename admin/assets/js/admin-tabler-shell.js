(function () {
  "use strict";

  const current = (location.pathname.split("/").pop() || "").toLowerCase();

  document.querySelectorAll("[data-admin-nav]").forEach((link) => {
    const href = (link.getAttribute("href") || "").split("/").pop().toLowerCase();
    link.classList.toggle("is-active", href === current);
  });

  document.querySelectorAll("[data-admin-logout]").forEach((button) => {
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
})();