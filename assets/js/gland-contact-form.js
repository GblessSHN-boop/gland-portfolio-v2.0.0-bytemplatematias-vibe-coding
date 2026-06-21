(function () {
  "use strict";

  const API_ENDPOINT = "/api/contact";

  function trim(value) {
    return String(value || "").trim();
  }

  function findField(form, selectors) {
    for (const selector of selectors) {
      const field = form.querySelector(selector);
      if (field) return field;
    }

    return null;
  }

  function findContactForm() {
    const direct = document.querySelector("form[data-gland-contact-form]");
    if (direct) return direct;

    const forms = Array.from(document.querySelectorAll("form"));

    return forms.find((form) => {
      const action = trim(form.getAttribute("action")).toLowerCase();
      const hasEmail = Boolean(form.querySelector('input[type="email"], input[name*="email" i], input[placeholder*="email" i]'));
      const hasMessage = Boolean(form.querySelector('textarea, [name*="message" i]'));

      return action.includes("/api/contact") || (hasEmail && hasMessage);
    });
  }

  function ensureStatus(form) {
    let status = form.querySelector("[data-gland-contact-status]");

    if (status) {
      return status;
    }

    status = document.createElement("div");
    status.setAttribute("data-gland-contact-status", "true");
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");

    status.style.display = "none";
    status.style.marginTop = "18px";
    status.style.padding = "14px 16px";
    status.style.borderRadius = "14px";
    status.style.fontWeight = "600";
    status.style.lineHeight = "1.5";

    const button = form.querySelector('button[type="submit"], button:not([type]), input[type="submit"]');

    if (button && button.parentElement) {
      button.parentElement.insertAdjacentElement("afterend", status);
    } else {
      form.appendChild(status);
    }

    return status;
  }

  function setStatus(status, type, message) {
    status.textContent = message;
    status.style.display = "block";

    if (type === "success") {
      status.style.background = "rgba(166, 255, 0, 0.14)";
      status.style.border = "1px solid rgba(166, 255, 0, 0.55)";
      status.style.color = "#d8ff7a";
      return;
    }

    if (type === "error") {
      status.style.background = "rgba(255, 80, 80, 0.12)";
      status.style.border = "1px solid rgba(255, 80, 80, 0.45)";
      status.style.color = "#ffb4b4";
      return;
    }

    status.style.background = "rgba(255, 255, 255, 0.08)";
    status.style.border = "1px solid rgba(255, 255, 255, 0.14)";
    status.style.color = "#ffffff";
  }

  function getPayload(form) {
    const nameField = findField(form, [
      '[name="name"]',
      '[name*="name" i]',
      'input[placeholder*="name" i]',
      'input[placeholder*="nama" i]',
      'input[type="text"]',
      'input:not([type])'
    ]);

    const emailField = findField(form, [
      '[name="email"]',
      '[name*="email" i]',
      'input[type="email"]',
      'input[placeholder*="email" i]'
    ]);

    const subjectField = findField(form, [
      '[name="subject"]',
      '[name*="subject" i]',
      'input[placeholder*="subject" i]',
      'input[placeholder*="subjek" i]'
    ]);

    const messageField = findField(form, [
      '[name="message"]',
      '[name*="message" i]',
      "textarea"
    ]);

    return {
      name: trim(nameField && nameField.value),
      email: trim(emailField && emailField.value),
      subject: trim(subjectField && subjectField.value) || "Website Contact Message",
      message: trim(messageField && messageField.value)
    };
  }

  function validate(payload) {
    if (!payload.name) return "Nama wajib diisi.";
    if (!payload.email) return "Email wajib diisi.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(payload.email)) return "Format email tidak valid.";
    if (!payload.message) return "Pesan wajib diisi.";
    if (payload.message.length < 3) return "Pesan terlalu pendek.";

    return "";
  }

  async function submitForm(form, status, button) {
    const payload = getPayload(form);
    const validationMessage = validate(payload);

    if (validationMessage) {
      setStatus(status, "error", validationMessage);
      return;
    }

    const originalText = button ? button.textContent : "";

    if (button) {
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      button.textContent = "Sending...";
    }

    setStatus(status, "info", "Sending message...");

    try {
      const response = await fetch(API_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify(payload)
      });

      let result = null;

      try {
        result = await response.json();
      } catch (error) {
        result = null;
      }

      if (!response.ok || !result || result.success !== true) {
        throw new Error((result && result.message) || "Message failed to send.");
      }

      form.reset();
      setStatus(status, "success", "Message sent successfully. I will get back to you soon.");

      if (typeof window.glandTrackEvent === "function") {
        window.glandTrackEvent("contact_form_submit_success", {
          source: "contact_page"
        });
      }
    } catch (error) {
      setStatus(status, "error", error.message || "Message failed to send. Please try again.");

      if (typeof window.glandTrackEvent === "function") {
        window.glandTrackEvent("contact_form_submit_failed", {
          source: "contact_page"
        });
      }
    } finally {
      if (button) {
        button.disabled = false;
        button.removeAttribute("aria-busy");
        button.textContent = originalText || "Send Message";
      }
    }
  }

  function boot() {
    const form = findContactForm();

    if (!form || form.dataset.glandContactFormReady === "true") {
      return;
    }

    form.dataset.glandContactFormReady = "true";
    form.setAttribute("action", API_ENDPOINT);
    form.setAttribute("method", "post");
    form.setAttribute("novalidate", "novalidate");

    const status = ensureStatus(form);
    const button = form.querySelector('button[type="submit"], button:not([type]), input[type="submit"]');

    if (button && button.tagName.toLowerCase() === "button") {
      button.setAttribute("type", "submit");
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      submitForm(form, status, button);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();