(function () {
  "use strict";

  const links = {
    "messages": "messages.html",
    "projects": "projects.html",
    "highlights": "highlights.html",
    "personal info": "personal-info.html",
    "hero content": "hero-content.html",
    "site identity": "site-identity.html",
    "dashboard": "dashboard.html",
    "analytics": "analytics.html",
    "page editor": "page-editor.html",
    "media": "media.html",
    "settings": "settings.html"
  };

  function normalize(text) {
    return String(text || "").trim().toLowerCase().replace(/\s+/g, " ");
  }

  function currentFile() {
    const path = location.pathname.split("/").pop() || "dashboard.html";
    return path.toLowerCase();
  }

  function repairNav() {
    const current = currentFile();

    document.querySelectorAll("aside a, .sidebar a, .admin-sidebar a, nav a").forEach((anchor) => {
      const label = normalize(anchor.textContent);

      Object.keys(links).forEach((key) => {
        if (label === key) {
          anchor.setAttribute("href", links[key]);
        }
      });

      const href = (anchor.getAttribute("href") || "").split("/").pop().toLowerCase();

      anchor.classList.toggle("active", href === current);
      anchor.removeAttribute("style");
    });

    document.querySelectorAll("button, a").forEach((element) => {
      const label = normalize(element.textContent);
      if (label === "logout") {
        element.textContent = "Sign Out";
      }
    });
  }

  function improvePageTitle() {
    const current = currentFile();

    const titles = {
      "dashboard.html": ["Dashboard", "Selamat datang kembali, Gland."],
      "messages.html": ["Contact Inbox", "Manage, review, and archive contact submissions from your public site."],
      "projects.html": ["Projects", "Create and manage portfolio projects."],
      "highlights.html": ["Highlights", "Manage selected highlights for the public portfolio."],
      "personal-info.html": ["Personal Info", "Manage profile and personal information."],
      "hero-content.html": ["Hero Content", "Manage hero section text and media."],
      "site-identity.html": ["Site Identity", "Manage brand, SEO metadata, logo paths, and social links."],
      "media.html": ["Media", "Upload and manage image or video assets."],
      "analytics.html": ["Analytics", "Review tracked events and traffic activity."],
      "page-editor.html": ["Page Editor", "Manage page-level content modules."],
      "settings.html": ["Settings", "Manage admin preferences and system settings."]
    };

    const data = titles[current];
    if (!data) return;

    document.title = data[0] + " | GLAND Admin";
  }

  function boot() {
    repairNav();
    improvePageTitle();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();