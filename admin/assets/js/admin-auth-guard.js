(function () {
  "use strict";

  if (window.__GLAND_ADMIN_AUTH_GUARD_LOADED__) {
    return;
  }

  window.__GLAND_ADMIN_AUTH_GUARD_LOADED__ = true;

  var path = window.location.pathname;

  if (path.indexOf("/admin/login.html") !== -1) {
    return;
  }

  function redirectToLogin() {
    var next = window.location.pathname + window.location.search;
    window.location.href = "/admin/login.html?next=" + encodeURIComponent(next);
  }

  function createLogoutButton() {
    if (document.querySelector("[data-gland-admin-logout]")) {
      return;
    }

    var button = document.createElement("button");
    button.type = "button";
    button.textContent = "Logout";
    button.setAttribute("data-gland-admin-logout", "true");
    button.style.position = "fixed";
    button.style.right = "18px";
    button.style.bottom = "18px";
    button.style.zIndex = "9999";
    button.style.border = "0";
    button.style.borderRadius = "999px";
    button.style.padding = "10px 16px";
    button.style.background = "#c9f31d";
    button.style.color = "#111";
    button.style.fontWeight = "800";
    button.style.cursor = "pointer";
    button.style.boxShadow = "0 10px 30px rgba(0,0,0,.25)";

    button.addEventListener("click", function () {
      fetch("/api/auth/logout", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Accept": "application/json",
          "Content-Type": "application/json"
        },
        body: "{}"
      })
        .finally(function () {
          window.location.href = "/admin/login.html";
        });
    });

    document.body.appendChild(button);
  }

  fetch("/api/auth/me", {
    method: "GET",
    credentials: "same-origin",
    headers: {
      "Accept": "application/json"
    }
  })
    .then(function (response) {
      if (!response.ok) {
        redirectToLogin();
        return null;
      }

      return response.json();
    })
    .then(function (payload) {
      if (!payload) {
        return;
      }

      if (!payload.authenticated) {
        redirectToLogin();
        return;
      }

      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", createLogoutButton);
      } else {
        createLogoutButton();
      }
    })
    .catch(function () {
      redirectToLogin();
    });
})();