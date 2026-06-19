/*
  GLAND PUBLIC CMS SYNC START
  Non-destructive frontend sync for public portfolio pages.
  It reads CMS API data and updates existing text, images, and links without rebuilding the approved layout.
*/
(function () {
  "use strict";

  if (window.__GLAND_CMS_PUBLIC_SYNC_LOADED__) {
    return;
  }

  window.__GLAND_CMS_PUBLIC_SYNC_LOADED__ = true;

  if (window.location.protocol === "file:") {
    return;
  }

  if (window.location.pathname.indexOf("/admin/") !== -1) {
    return;
  }

  var API = {
    personalInfo: "/api/personal-info",
    heroContent: "/api/hero-content",
    siteIdentity: "/api/site-identity",
    highlights: "/api/highlights",
    projects: "/api/projects",
    mediaFiles: "/api/media-files"
  };

  function fetchJson(url) {
    return fetch(url, {
      method: "GET",
      headers: {
        "Accept": "application/json"
      },
      credentials: "same-origin"
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error(url + " returned " + response.status);
        }

        return response.json();
      })
      .catch(function () {
        return null;
      });
  }

  function unwrapResponse(response) {
    if (!response) {
      return null;
    }

    if (Object.prototype.hasOwnProperty.call(response, "data")) {
      return response.data;
    }

    return response;
  }

  function firstRecord(value) {
    var data = unwrapResponse(value);

    if (!data) {
      return null;
    }

    if (Array.isArray(data)) {
      return data.length ? data[0] : null;
    }

    if (Array.isArray(data.items)) {
      return data.items.length ? data.items[0] : null;
    }

    if (Array.isArray(data.records)) {
      return data.records.length ? data.records[0] : null;
    }

    if (Array.isArray(data.results)) {
      return data.results.length ? data.results[0] : null;
    }

    if (data.item && typeof data.item === "object") {
      return data.item;
    }

    if (data.record && typeof data.record === "object") {
      return data.record;
    }

    return data;
  }

  function listRecords(value) {
    var data = unwrapResponse(value);

    if (!data) {
      return [];
    }

    if (Array.isArray(data)) {
      return data;
    }

    if (Array.isArray(data.items)) {
      return data.items;
    }

    if (Array.isArray(data.records)) {
      return data.records;
    }

    if (Array.isArray(data.results)) {
      return data.results;
    }

    if (Array.isArray(data.projects)) {
      return data.projects;
    }

    if (Array.isArray(data.highlights)) {
      return data.highlights;
    }

    if (Array.isArray(data.media_files)) {
      return data.media_files;
    }

    if (data.item && typeof data.item === "object") {
      return [data.item];
    }

    if (data.record && typeof data.record === "object") {
      return [data.record];
    }

    if (typeof data === "object") {
      return [data];
    }

    return [];
  }

  function pick(object, keys) {
    if (!object || typeof object !== "object") {
      return "";
    }

    for (var i = 0; i < keys.length; i += 1) {
      var key = keys[i];
      var value = object[key];

      if (value !== null && value !== undefined && String(value).trim() !== "") {
        return String(value).trim();
      }
    }

    return "";
  }

  function setText(element, value) {
    if (!element || !value) {
      return;
    }

    element.textContent = value;
  }

  function setHtmlLineBreaks(element, value) {
    if (!element || !value) {
      return;
    }

    var lines = String(value)
      .split(/\r?\n/)
      .map(function (line) {
        return line.trim();
      })
      .filter(Boolean);

    if (!lines.length) {
      return;
    }

    element.innerHTML = lines
      .map(function (line) {
        return escapeHtml(line);
      })
      .join("<br>");
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function updateMeta(name, content) {
    if (!name || !content) {
      return;
    }

    var selector = 'meta[name="' + name + '"]';
    var meta = document.querySelector(selector);

    if (!meta) {
      meta = document.createElement("meta");
      meta.setAttribute("name", name);
      document.head.appendChild(meta);
    }

    meta.setAttribute("content", content);
  }

  function updatePropertyMeta(property, content) {
    if (!property || !content) {
      return;
    }

    var selector = 'meta[property="' + property + '"]';
    var meta = document.querySelector(selector);

    if (!meta) {
      meta = document.createElement("meta");
      meta.setAttribute("property", property);
      document.head.appendChild(meta);
    }

    meta.setAttribute("content", content);
  }

  function updateCanonical(url) {
    if (!url) {
      return;
    }

    var link = document.querySelector('link[rel="canonical"]');

    if (!link) {
      link = document.createElement("link");
      link.setAttribute("rel", "canonical");
      document.head.appendChild(link);
    }

    link.setAttribute("href", url);
  }

  function updateFavicon(url) {
    if (!url) {
      return;
    }

    var icon = document.querySelector('link[rel="icon"], link[rel="shortcut icon"]');

    if (!icon) {
      icon = document.createElement("link");
      icon.setAttribute("rel", "icon");
      document.head.appendChild(icon);
    }

    icon.setAttribute("href", url);
  }

  function findTextElement(exactText) {
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    var node;

    while ((node = walker.nextNode())) {
      if (node.nodeValue && node.nodeValue.trim() === exactText) {
        return node.parentElement;
      }
    }

    return null;
  }

  function replaceExactText(oldText, newText) {
    if (!oldText || !newText || oldText === newText) {
      return;
    }

    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    var node;

    while ((node = walker.nextNode())) {
      if (node.nodeValue && node.nodeValue.trim() === oldText) {
        node.nodeValue = node.nodeValue.replace(oldText, newText);
      }
    }
  }

  function updateLinkByHrefContains(fragment, newHref, newText) {
    if (!fragment || !newHref) {
      return;
    }

    var links = Array.prototype.slice.call(document.querySelectorAll("a[href]"));

    links.forEach(function (link) {
      var href = link.getAttribute("href") || "";

      if (href.indexOf(fragment) !== -1) {
        link.setAttribute("href", newHref);

        if (newText && link.textContent.trim()) {
          link.textContent = newText;
        }
      }
    });
  }

  function updateImageBySrcContains(fragment, newSrc, newAlt) {
    if (!fragment || !newSrc) {
      return;
    }

    var images = Array.prototype.slice.call(document.querySelectorAll("img[src]"));

    images.forEach(function (image) {
      var src = image.getAttribute("src") || "";

      if (src.indexOf(fragment) !== -1) {
        image.setAttribute("src", newSrc);

        if (newAlt) {
          image.setAttribute("alt", newAlt);
        }
      }
    });
  }

  function normalizeMediaPath(path) {
    if (!path) {
      return "";
    }

    var value = String(path).trim();

    if (/^(https?:)?\/\//i.test(value) || value.indexOf("data:") === 0 || value.indexOf("/") === 0) {
      return value;
    }

    return value.replace(/\\/g, "/");
  }

  function getActiveItems(items) {
    return items
      .filter(function (item) {
        var status = pick(item, ["status", "is_active", "active", "visibility"]);

        if (!status) {
          return true;
        }

        status = status.toLowerCase();

        return status !== "0" && status !== "false" && status !== "inactive" && status !== "hidden" && status !== "draft";
      })
      .sort(function (a, b) {
        var orderA = Number(pick(a, ["sort_order", "display_order", "position", "order"]) || 9999);
        var orderB = Number(pick(b, ["sort_order", "display_order", "position", "order"]) || 9999);

        if (orderA !== orderB) {
          return orderA - orderB;
        }

        return Number(pick(b, ["id"]) || 0) - Number(pick(a, ["id"]) || 0);
      });
  }

  function syncSiteIdentity(siteIdentity) {
    var site = firstRecord(siteIdentity);

    if (!site) {
      return;
    }

    var title = pick(site, ["site_title", "title", "meta_title", "page_title"]);
    var description = pick(site, ["meta_description", "description", "seo_description"]);
    var canonical = pick(site, ["canonical_url", "canonical", "site_url"]);
    var favicon = normalizeMediaPath(pick(site, ["favicon_url", "favicon", "favicon_path", "logo_icon"]));
    var ogImage = normalizeMediaPath(pick(site, ["og_image", "og_image_url", "social_image"]));

    if (title) {
      document.title = title;
      updatePropertyMeta("og:title", title);
      updateMeta("twitter:title", title);
    }

    if (description) {
      updateMeta("description", description);
      updatePropertyMeta("og:description", description);
      updateMeta("twitter:description", description);
    }

    if (canonical) {
      updateCanonical(canonical);
      updatePropertyMeta("og:url", canonical);
    }

    if (favicon) {
      updateFavicon(favicon);
    }

    if (ogImage) {
      updatePropertyMeta("og:image", ogImage);
      updateMeta("twitter:image", ogImage);
    }
  }

  function syncHero(heroContent) {
    var hero = firstRecord(heroContent);

    if (!hero) {
      return;
    }

    var titleLine1 = pick(hero, ["title_line_1", "title_first_line", "headline_line_1", "profession_title_1", "primary_title"]);
    var titleLine2 = pick(hero, ["title_line_2", "title_second_line", "headline_line_2", "profession_title_2", "secondary_title"]);
    var titleCombined = pick(hero, ["title", "headline", "hero_title"]);
    var availabilityLine1 = pick(hero, ["availability_line_1", "availability_text", "availability"]);
    var availabilityLine2 = pick(hero, ["availability_line_2", "availability_location", "availability_scope"]);
    var phoneText = pick(hero, ["phone_text", "phone", "phone_number"]);
    var phoneUrl = pick(hero, ["phone_url", "whatsapp_url", "contact_url"]);
    var introText = pick(hero, ["intro_video_text", "video_text", "video_label"]);
    var introUrl = pick(hero, ["intro_video_url", "video_url", "youtube_url"]);
    var videoSrc = normalizeMediaPath(pick(hero, ["hero_video_url", "hero_video", "video_src", "right_video_url", "right_video"]));

    if (titleLine1) {
      replaceExactText("AI Engineer", titleLine1);
    }

    if (titleLine2) {
      replaceExactText("Creative Designer", titleLine2);
    }

    if (!titleLine1 && !titleLine2 && titleCombined) {
      var heroTitleElement = findTextElement("AI Engineer") || document.querySelector(".hero-title, .banner-title, h1");

      if (heroTitleElement) {
        setHtmlLineBreaks(heroTitleElement, titleCombined);
      }
    }

    if (availabilityLine1) {
      replaceExactText("Available for AI, Vibe Coding, UI/UX, and Design Projects", availabilityLine1);
    }

    if (availabilityLine2) {
      replaceExactText("Worldwide", availabilityLine2);
    }

    if (phoneText) {
      replaceExactText("(+62)-895-4048-71011", phoneText);
    }

    if (phoneUrl) {
      updateLinkByHrefContains("wa.me", phoneUrl, phoneText);
    }

    if (introText) {
      replaceExactText("Intro Video", introText);
    }

    if (introUrl) {
      updateLinkByHrefContains("youtube.com/watch", introUrl, introText);
      updateLinkByHrefContains("youtu.be", introUrl, introText);
    }

    if (videoSrc) {
      var videos = Array.prototype.slice.call(document.querySelectorAll("video source, video"));

      videos.forEach(function (video) {
        var src = video.getAttribute("src") || "";

        if (src.indexOf("hero-right") !== -1 || src.indexOf("iklan") !== -1 || src.indexOf("assets/video") !== -1) {
          video.setAttribute("src", videoSrc);

          if (video.parentElement && video.parentElement.tagName.toLowerCase() === "video") {
            try {
              video.parentElement.load();
            } catch (error) {
              // Ignore video reload errors.
            }
          }
        }
      });
    }
  }

  function syncPersonalInfo(personalInfo) {
    var info = firstRecord(personalInfo);

    if (!info) {
      return;
    }

    var name = pick(info, ["full_name", "name", "display_name"]);
    var intro = pick(info, ["intro_text", "about_intro", "short_intro", "summary"]);
    var description = pick(info, ["description", "bio", "about_description"]);
    var email = pick(info, ["email", "email_address"]);
    var phone = pick(info, ["phone", "phone_number"]);
    var address = pick(info, ["address", "location"]);
    var image = normalizeMediaPath(pick(info, ["image_url", "image_path", "photo_url", "photo", "profile_image"]));

    if (name) {
      replaceExactText("I'm Gland Jermano Blessed Siahaan.", "I'm " + name + ".");
    }

    if (intro) {
      var introElement = findTextElement("A college student from Medan, Indonesia.") || findTextElement("I shape digital ideas through AI, design, and strategy");

      if (introElement) {
        setHtmlLineBreaks(introElement, intro);
      }
    }

    if (description) {
      replaceExactText(
        "I'm a college student from Medan, Indonesia, shaping digital ideas through AI, design, and strategy. I enjoy building clean web experiences, creative visuals, and meaningful digital solutions that feel alive and professional.",
        description
      );
    }

    if (email) {
      replaceExactText("glandjermanoblessedsiahaan@gmail.com", email);
      updateLinkByHrefContains("mailto:", "mailto:" + email, email);
    }

    if (phone) {
      replaceExactText("(+62)-895-4048-71011", phone);
    }

    if (address) {
      replaceExactText("Medan, Indonesia", address);
    }

    if (image) {
      updateImageBySrcContains("gland-personal-info", image, name || "Gland personal info");
    }
  }

  function syncHighlights(highlightsResponse) {
    var highlights = getActiveItems(listRecords(highlightsResponse));

    if (!highlights.length) {
      return;
    }

    var oldHighlights = [
      "AI Product Thinking | Interface Strategy | 2026",
      "Creative Automation | Prompt Engineering | 2025",
      "Frontend Portfolio System | Web Interaction Design | 2026",
      "Human-AI Experience | UX Prototype Design | 2025"
    ];

    highlights.slice(0, oldHighlights.length).forEach(function (highlight, index) {
      var title = pick(highlight, ["title", "name", "highlight_title"]);
      var category = pick(highlight, ["category", "subtitle", "type", "role"]);
      var year = pick(highlight, ["year", "period", "date_label"]);

      var line = [title, category, year].filter(Boolean).join(" | ");

      if (line) {
        replaceExactText(oldHighlights[index], line);
      }
    });
  }

  function syncProjects(projectsResponse) {
    var projects = getActiveItems(listRecords(projectsResponse));

    if (!projects.length) {
      return;
    }

    var firstProject = projects[0];

    var title = pick(firstProject, ["title", "name", "project_title"]);
    var category = pick(firstProject, ["category", "project_category", "type"]);
    var image = normalizeMediaPath(pick(firstProject, ["image_url", "image_path", "cover_image", "cover_url", "thumbnail"]));
    var url = pick(firstProject, ["project_url", "live_url", "url", "demo_url", "link"]);

    if (title) {
      replaceExactText("GLAND Personal Portfolio Website", title);
    }

    if (category) {
      replaceExactText("AI Web Portfolio", category);
    }

    if (image) {
      updateImageBySrcContains("gland-portfolio-website-cover", image, title || "Project cover");
    }

    if (url) {
      var projectLinks = Array.prototype.slice.call(document.querySelectorAll('a[href*="project"], a[href*="portfolio"], a[href*="protfolio"]'));

      projectLinks.slice(0, 3).forEach(function (link) {
        var text = link.textContent.trim();

        if (!text || text.indexOf("GLAND") !== -1 || text.toLowerCase().indexOf("portfolio") !== -1 || text.toLowerCase().indexOf("project") !== -1) {
          link.setAttribute("href", url);
        }
      });
    }
  }

  function syncMedia(mediaResponse) {
    var media = getActiveItems(listRecords(mediaResponse));

    if (!media.length) {
      return;
    }

    var headerIcon = media.find(function (item) {
      var label = [
        pick(item, ["title", "name", "alt_text", "description"]),
        pick(item, ["file_name", "filename", "original_name"]),
        pick(item, ["file_path", "url", "path"])
      ].join(" ").toLowerCase();

      return label.indexOf("header") !== -1 && label.indexOf("icon") !== -1;
    });

    if (headerIcon) {
      var headerIconPath = normalizeMediaPath(pick(headerIcon, ["file_path", "url", "path", "public_url"]));
      updateImageBySrcContains("gland-header-icon", headerIconPath, "Gland header icon");
    }
  }

  function syncAll() {
    Promise.all([
      fetchJson(API.siteIdentity),
      fetchJson(API.heroContent),
      fetchJson(API.personalInfo),
      fetchJson(API.highlights),
      fetchJson(API.projects),
      fetchJson(API.mediaFiles)
    ]).then(function (results) {
      syncSiteIdentity(results[0]);
      syncHero(results[1]);
      syncPersonalInfo(results[2]);
      syncHighlights(results[3]);
      syncProjects(results[4]);
      syncMedia(results[5]);

      document.documentElement.setAttribute("data-gland-cms-sync", "ready");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", syncAll);
  } else {
    syncAll();
  }
})();
/* GLAND PUBLIC CMS SYNC END */