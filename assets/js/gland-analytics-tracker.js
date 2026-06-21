/*
  GLAND PUBLIC ANALYTICS TRACKER START
  Tracks public portfolio visits and interaction events.
  Backend endpoints:
  - POST /api/analytics/visit
  - POST /api/analytics/event
*/
(function () {
  "use strict";

  var VISIT_ENDPOINT = "/api/analytics/visit";
  var EVENT_ENDPOINT = "/api/analytics/event";
  var VISITOR_KEY = "gland_analytics_visitor_id";
  var SESSION_KEY = "gland_analytics_session_id";
  var SESSION_STARTED_KEY = "gland_analytics_session_started_at";

  if (window.__GLAND_ANALYTICS_TRACKER_LOADED__) {
    return;
  }

  window.__GLAND_ANALYTICS_TRACKER_LOADED__ = true;

  if (window.location.protocol === "file:") {
    return;
  }

  if (window.location.pathname.indexOf("/admin/") !== -1) {
    return;
  }

  function safeStorage(type) {
    try {
      var storage = window[type];
      var testKey = "__gland_storage_test__";
      storage.setItem(testKey, "1");
      storage.removeItem(testKey);
      return storage;
    } catch (error) {
      return null;
    }
  }

  var local = safeStorage("localStorage");
  var session = safeStorage("sessionStorage");

  function createId(prefix) {
    var value = "";

    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      value = window.crypto.randomUUID();
    } else {
      value = String(Date.now()) + "-" + Math.random().toString(16).slice(2) + "-" + Math.random().toString(16).slice(2);
    }

    return prefix + "_" + value;
  }

  function getOrCreateStorageValue(storage, key, prefix) {
    if (!storage) {
      return createId(prefix);
    }

    var currentValue = storage.getItem(key);
    if (currentValue) {
      return currentValue;
    }

    var newValue = createId(prefix);
    storage.setItem(key, newValue);
    return newValue;
  }

  var visitorId = getOrCreateStorageValue(local, VISITOR_KEY, "visitor");
  var sessionId = getOrCreateStorageValue(session, SESSION_KEY, "session");

  if (session && !session.getItem(SESSION_STARTED_KEY)) {
    session.setItem(SESSION_STARTED_KEY, new Date().toISOString());
  }

  var pageStartedAt = Date.now();
  var maxScrollDepth = 0;
  var sentScrollMilestones = {};
  var scrollMilestones = [25, 50, 75, 90, 100];

  function getBrowserName() {
    var ua = navigator.userAgent || "";

    if (/Edg\//.test(ua)) return "Edge";
    if (/OPR\//.test(ua) || /Opera/.test(ua)) return "Opera";
    if (/Firefox\//.test(ua)) return "Firefox";
    if (/Chrome\//.test(ua) && !/Edg\//.test(ua) && !/OPR\//.test(ua)) return "Chrome";
    if (/Safari\//.test(ua) && !/Chrome\//.test(ua)) return "Safari";

    return "Unknown";
  }

  function getDeviceType() {
    var ua = navigator.userAgent || "";
    var width = window.innerWidth || document.documentElement.clientWidth || 0;

    if (/Mobi|Android|iPhone|iPod/i.test(ua) || width <= 767) {
      return "mobile";
    }

    if (/Tablet|iPad/i.test(ua) || (width >= 768 && width <= 1024)) {
      return "tablet";
    }

    return "desktop";
  }

  function getPagePath() {
    return window.location.pathname + window.location.search;
  }

  function getDurationSeconds() {
    return Math.max(0, Math.round((Date.now() - pageStartedAt) / 1000));
  }

  function getScrollDepth() {
    var doc = document.documentElement;
    var body = document.body;

    var scrollTop = window.pageYOffset || doc.scrollTop || body.scrollTop || 0;
    var scrollHeight = Math.max(
      body.scrollHeight,
      body.offsetHeight,
      doc.clientHeight,
      doc.scrollHeight,
      doc.offsetHeight
    );

    var viewportHeight = window.innerHeight || doc.clientHeight || 0;
    var trackableHeight = scrollHeight - viewportHeight;

    if (trackableHeight <= 0) {
      return 100;
    }

    var depth = Math.round((scrollTop / trackableHeight) * 100);
    return Math.max(0, Math.min(100, depth));
  }

  function commonPayload(extra) {
    var payload = {
      visitor_id: visitorId,
      session_id: sessionId,
      page_path: getPagePath(),
      referrer: document.referrer || "",
      device_type: getDeviceType(),
      browser_name: getBrowserName(),
      duration_seconds: getDurationSeconds(),
      scroll_depth: maxScrollDepth,
      user_agent: navigator.userAgent || "",
      occurred_at: new Date().toISOString()
    };

    if (extra && typeof extra === "object") {
      Object.keys(extra).forEach(function (key) {
        payload[key] = extra[key];
      });
    }

    return payload;
  }

  function postJson(url, payload, preferBeacon) {
    var body = JSON.stringify(payload);

    if (preferBeacon && navigator.sendBeacon) {
      try {
        var blob = new Blob([body], { type: "application/json" });
        if (navigator.sendBeacon(url, blob)) {
          return;
        }
      } catch (error) {
        // Fall back to fetch.
      }
    }

    try {
      fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: body,
        credentials: "same-origin",
        keepalive: Boolean(preferBeacon)
      }).catch(function () {
        // Analytics should never break the public portfolio.
      });
    } catch (error) {
      // Quiet fail. Layout first, analytics second. Civilization may survive.
    }
  }

  function trackVisit() {
    postJson(VISIT_ENDPOINT, commonPayload({
      visit_type: "page_view"
    }), false);
  }

  function trackEvent(eventType, metadata, preferBeacon) {
    postJson(EVENT_ENDPOINT, commonPayload({
      event_type: eventType,
      event_name: eventType,
      event_label: metadata && metadata.label ? metadata.label : "",
      metadata: metadata || {}
    }), Boolean(preferBeacon));
  }

  function getLinkLabel(link) {
    var text = (link.innerText || link.textContent || "").trim();
    var title = link.getAttribute("title") || "";
    var aria = link.getAttribute("aria-label") || "";

    return text || title || aria || link.href || "Unknown link";
  }

  function getSocialPlatform(url) {
    var normalizedUrl = String(url || "").toLowerCase();

    if (normalizedUrl.indexOf("youtube.com") !== -1 || normalizedUrl.indexOf("youtu.be") !== -1) return "youtube";
    if (normalizedUrl.indexOf("github.com") !== -1) return "github";
    if (normalizedUrl.indexOf("instagram.com") !== -1) return "instagram";
    if (normalizedUrl.indexOf("linkedin.com") !== -1) return "linkedin";
    if (normalizedUrl.indexOf("wa.me") !== -1 || normalizedUrl.indexOf("whatsapp.com") !== -1) return "whatsapp";

    return "";
  }

  function isIntroVideoLink(link) {
    var href = String(link.href || "").toLowerCase();
    var label = getLinkLabel(link).toLowerCase();

    if (label.indexOf("intro video") !== -1 || label.indexOf("intro") !== -1) {
      return true;
    }

    if ((href.indexOf("youtube.com/watch") !== -1 || href.indexOf("youtu.be/") !== -1) && label.indexOf("video") !== -1) {
      return true;
    }

    return false;
  }

  function isProjectLink(link) {
    var href = String(link.getAttribute("href") || "").toLowerCase();
    var className = String(link.className || "").toLowerCase();
    var parent = link.closest('[class*="project"], [class*="portfolio"], [class*="protfolio"], [id*="project"], [id*="portfolio"], [id*="protfolio"]');

    if (parent) {
      return true;
    }

    if (
      href.indexOf("project") !== -1 ||
      href.indexOf("portfolio") !== -1 ||
      href.indexOf("protfolio") !== -1 ||
      className.indexOf("project") !== -1 ||
      className.indexOf("portfolio") !== -1 ||
      className.indexOf("protfolio") !== -1
    ) {
      return true;
    }

    return false;
  }

  function handleDocumentClick(event) {
    var link = event.target.closest ? event.target.closest("a") : null;

    if (!link) {
      return;
    }

    var href = link.href || "";
    var label = getLinkLabel(link);

    if (isIntroVideoLink(link)) {
      trackEvent("intro_video_view", {
        label: label,
        href: href
      }, true);
      return;
    }

    var platform = getSocialPlatform(href);
    if (platform) {
      trackEvent("social_click", {
        label: label,
        href: href,
        platform: platform
      }, true);
      return;
    }

    if (isProjectLink(link)) {
      trackEvent("project_click", {
        label: label,
        href: href
      }, true);
    }
  }

  function handleContactSubmit(event) {
    var form = event.target;

    if (!form || !form.matches || !form.matches("form")) {
      return;
    }

    var action = String(form.getAttribute("action") || "").toLowerCase();
    var id = form.getAttribute("id") || "";
    var className = String(form.className || "").toLowerCase();

    if (
      action.indexOf("/api/contact") !== -1 ||
      id.toLowerCase().indexOf("contact") !== -1 ||
      className.indexOf("contact") !== -1 ||
      window.location.pathname.toLowerCase().indexOf("contact") !== -1
    ) {
      trackEvent("contact_submit", {
        label: "Contact form submit",
        form_id: id,
        form_action: form.getAttribute("action") || ""
      }, true);
    }
  }

  function handleVideoPlay(event) {
    var video = event.target;

    if (!video || !video.matches || !video.matches("video")) {
      return;
    }

    var src = video.currentSrc || video.getAttribute("src") || "";
    var label = video.getAttribute("title") || video.getAttribute("aria-label") || "Public video play";

    trackEvent("intro_video_view", {
      label: label,
      src: src
    }, true);
  }

  function handleScroll() {
    var depth = getScrollDepth();

    if (depth > maxScrollDepth) {
      maxScrollDepth = depth;
    }

    scrollMilestones.forEach(function (milestone) {
      if (depth >= milestone && !sentScrollMilestones[milestone]) {
        sentScrollMilestones[milestone] = true;

        trackEvent("scroll_depth", {
          label: String(milestone) + "%",
          depth: milestone
        }, false);
      }
    });
  }

  function throttle(callback, delay) {
    var waiting = false;

    return function () {
      if (waiting) {
        return;
      }

      waiting = true;

      window.setTimeout(function () {
        waiting = false;
        callback();
      }, delay);
    };
  }

  function sendPageDuration() {
    trackEvent("page_duration", {
      label: "Page duration",
      duration_seconds: getDurationSeconds(),
      max_scroll_depth: maxScrollDepth
    }, true);
  }

  function init() {
    maxScrollDepth = getScrollDepth();

    trackVisit();

    document.addEventListener("click", handleDocumentClick, true);
    document.addEventListener("submit", handleContactSubmit, true);
    document.addEventListener("play", handleVideoPlay, true);

    window.addEventListener("scroll", throttle(handleScroll, 800), { passive: true });
    window.addEventListener("pagehide", sendPageDuration);
    window.addEventListener("beforeunload", sendPageDuration);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
/* GLAND PUBLIC ANALYTICS TRACKER END */