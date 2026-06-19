(function () {
  "use strict";

  var form = document.getElementById("forgotPasswordForm");
  var button = document.getElementById("forgotButton");
  var message = document.getElementById("forgotMessage");
  var COOLDOWN_KEY = "gland_admin_password_reset_cooldown_until";
  var timerId = null;

  function setMessage(value, isHtml) {
    if (!message) {
      return;
    }

    if (isHtml) {
      message.innerHTML = value || "";
      return;
    }

    message.textContent = value || "";
  }

  function getCooldownUntil() {
    var raw = window.localStorage.getItem(COOLDOWN_KEY);
    if (!raw) {
      return 0;
    }

    var parsed = parseInt(raw, 10);
    return isNaN(parsed) ? 0 : parsed;
  }

  function setCooldown(seconds) {
    var safeSeconds = Math.max(0, parseInt(seconds || 0, 10));
    if (!safeSeconds) {
      window.localStorage.removeItem(COOLDOWN_KEY);
      refreshButton();
      return;
    }

    var until = Date.now() + (safeSeconds * 1000);
    window.localStorage.setItem(COOLDOWN_KEY, String(until));
    refreshButton();
  }

  function getRemainingSeconds() {
    var until = getCooldownUntil();
    if (!until) {
      return 0;
    }

    var remaining = Math.ceil((until - Date.now()) / 1000);
    return remaining > 0 ? remaining : 0;
  }

  function refreshButton() {
    if (!button) {
      return;
    }

    var remaining = getRemainingSeconds();

    if (remaining > 0) {
      button.disabled = true;
      button.textContent = "Send Reset Link (" + remaining + "s)";
      return;
    }

    window.localStorage.removeItem(COOLDOWN_KEY);
    button.disabled = false;
    button.textContent = "Send Reset Link";
  }

  function startTimer() {
    if (timerId) {
      window.clearInterval(timerId);
    }

    refreshButton();

    timerId = window.setInterval(function () {
      refreshButton();

      if (getRemainingSeconds() <= 0 && timerId) {
        window.clearInterval(timerId);
        timerId = null;
      }
    }, 1000);
  }

  if (!form) {
    return;
  }

  startTimer();

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    if (getRemainingSeconds() > 0) {
      setMessage("Please wait " + getRemainingSeconds() + " seconds before requesting another reset email.");
      return;
    }

    var identifierInput = document.getElementById("identifier");
    var identifier = identifierInput ? identifierInput.value.trim() : "";

    if (!identifier) {
      setMessage("Username or email is required.");
      return;
    }

    button.disabled = true;
    button.textContent = "Sending...";
    setMessage("");

    fetch("/api/auth/forgot-password", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        identifier: identifier
      })
    })
      .then(function (response) {
        return response.json().then(function (payload) {
          return {
            ok: response.ok,
            payload: payload || {}
          };
        });
      })
      .then(function (result) {
        var payload = result.payload || {};
        var data = payload.data || {};

        if (data.retry_after_seconds) {
          setCooldown(data.retry_after_seconds);
          startTimer();
        }

        if (data.cooldown_seconds && payload.success) {
          setCooldown(data.cooldown_seconds);
          startTimer();
        }

        if (!result.ok || !payload.success) {
          throw new Error(payload.message || "Failed to request password reset.");
        }

        var debugUrl = data.debug_reset_url;

        if (debugUrl) {
          setMessage(
            "Reset link sent. Local debug link: <a href=\"" + debugUrl + "\">Open reset link</a>",
            true
          );
          return;
        }

        setMessage("A reset email has been sent. Please check your Gmail inbox.");
      })
      .catch(function (error) {
        setMessage(error.message || "Failed to request password reset.");
      })
      .finally(function () {
        refreshButton();
        startTimer();
      });
  });
})();