(function () {
  "use strict";

  document.documentElement.setAttribute("data-gland-admin-polish", "ready");

  function normalizePath(value) {
    try {
      return new URL(value, window.location.origin).pathname.replace(/\/+$/, "");
    } catch (error) {
      return String(value || "").split("?")[0].replace(/\/+$/, "");
    }
  }

  function markActiveNav() {
    var currentPath = normalizePath(window.location.pathname);
    var links = document.querySelectorAll("a[href]");

    links.forEach(function (link) {
      var href = link.getAttribute("href");

      if (!href || href.charAt(0) === "#" || href.indexOf("javascript:") === 0) {
        return;
      }

      var linkPath = normalizePath(href);

      if (!linkPath) {
        return;
      }

      if (linkPath === currentPath) {
        link.classList.add("is-active");
        link.setAttribute("aria-current", "page");
      }
    });
  }

  function markBody() {
    document.body.classList.add("gland-admin-polished");

    var pageName = window.location.pathname
      .split("/")
      .filter(Boolean)
      .pop() || "dashboard.html";

    document.body.setAttribute("data-admin-page", pageName.replace(".html", ""));
  }

  function improveExternalLinks() {
    document.querySelectorAll('a[target="_blank"]').forEach(function (link) {
      var rel = link.getAttribute("rel") || "";
      if (rel.indexOf("noopener") === -1) {
        rel = (rel + " noopener noreferrer").trim();
      }
      link.setAttribute("rel", rel);
    });
  }

  function run() {
    if (!document.body) {
      return;
    }

    markBody();
    markActiveNav();
    improveExternalLinks();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();