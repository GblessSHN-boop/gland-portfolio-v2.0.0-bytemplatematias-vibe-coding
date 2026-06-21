(function () {
  "use strict";

  window.__GLAND_AUTH_JS_VERSION__ = "loginfix-2step-v2";

  var form = document.getElementById("adminLoginForm");
  var message = document.getElementById("loginMessage");
  var button = document.getElementById("loginButton");

  var verificationState = {
    active: false,
    challengeToken: "",
    username: ""
  };

  function getNextUrl() {
    var params = new URLSearchParams(window.location.search);
    var next = params.get("next");

    if (next && next.indexOf("/admin/") === 0 && next.indexOf("/admin/login.html") !== 0) {
      return next;
    }

    return "/admin/dashboard.html";
  }

  function setMessage(value, type) {
    if (!message) return;

    message.classList.remove("is-success", "is-warning", "is-danger");
    message.classList.add(type || "is-danger");
    message.innerHTML = value || "";
  }

  function setLoading(isLoading) {
    if (!button) return;

    button.disabled = isLoading;

    if (verificationState.active) {
      button.textContent = isLoading ? "Verifying..." : "Verify & Login";
    } else {
      button.textContent = isLoading ? "Checking..." : "Login";
    }
  }

  function getVerificationStep() {
    return document.getElementById("loginVerificationStep");
  }

  function getVerificationInput() {
    return document.getElementById("verificationCode");
  }

  function resetVerificationMode() {
    verificationState.active = false;
    verificationState.challengeToken = "";
    verificationState.username = "";

    var usernameInput = document.getElementById("username");
    var passwordInput = document.getElementById("password");
    var codeInput = getVerificationInput();
    var wrapper = getVerificationStep();

    if (usernameInput) usernameInput.disabled = false;
    if (passwordInput) {
      passwordInput.disabled = false;
      passwordInput.value = "";
    }
    if (codeInput) codeInput.value = "";
    if (wrapper) wrapper.hidden = true;

    setMessage("");
    setLoading(false);
  }

  function bindRestartButton() {
    var restartButton = document.getElementById("restartLoginButton");

    if (!restartButton || restartButton.dataset.bound === "true") return;

    restartButton.dataset.bound = "true";
    restartButton.addEventListener("click", resetVerificationMode);
  }

  function enterVerificationMode(payload, username) {
    var data = (payload && payload.data) || {};
    var wrapper = getVerificationStep();
    var hint = document.getElementById("verificationHint");
    var usernameInput = document.getElementById("username");
    var passwordInput = document.getElementById("password");
    var codeInput = getVerificationInput();

    verificationState.active = true;
    verificationState.challengeToken = data.challenge_token || "";
    verificationState.username = username || "";

    if (!verificationState.challengeToken) {
      setMessage("Verification token missing from server response. Login flow needs backend check.");
      verificationState.active = false;
      return;
    }

    if (usernameInput) usernameInput.disabled = true;
    if (passwordInput) passwordInput.disabled = true;
    if (wrapper) wrapper.hidden = false;

    var hintParts = [];

    if (data.masked_email) {
      hintParts.push("Code sent to " + data.masked_email + ".");
    } else {
      hintParts.push("Enter the 6-digit code for this login attempt.");
    }

    if (data.expires_at) {
      hintParts.push("Expires at " + data.expires_at + ".");
    }

    if (data.debug_code) {
      hintParts.push('<span class="debug-code">Development code: <strong>' + String(data.debug_code) + '</strong></span>');
    } else if (!data.email_sent) {
      hintParts.push('<span class="debug-code">Email is not confirmed. Check SMTP config if no code arrives.</span>');
    }

    if (hint) {
      hint.innerHTML = hintParts.join(" ");
    }

    setMessage("Password accepted. Enter the verification code.", "is-success");
    setLoading(false);

    if (codeInput) {
      codeInput.focus();
      codeInput.select();
    }
  }

  function checkExistingSession() {
    fetch("/api/auth/me", {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        "Accept": "application/json"
      }
    })
      .then(function (response) {
        if (!response.ok) return null;
        return response.json();
      })
      .then(function (payload) {
        if (payload && payload.authenticated) {
          window.location.replace(getNextUrl());
        }
      })
      .catch(function () {});
  }

  function submitPasswordLogin() {
    var usernameInput = document.getElementById("username");
    var passwordInput = document.getElementById("password");

    var username = usernameInput ? usernameInput.value.trim() : "";
    var password = passwordInput ? passwordInput.value : "";

    if (!username || !password) {
      setMessage("Username and password are required.");
      return Promise.resolve();
    }

    setLoading(true);
    setMessage("");

    return fetch("/api/auth/login", {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        username: username,
        password: password
      })
    })
      .then(function (response) {
        return response.json().catch(function () {
          return {};
        }).then(function (payload) {
          return { ok: response.ok, status: response.status, payload: payload };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.payload || !result.payload.success) {
          throw new Error((result.payload && (result.payload.message || result.payload.error)) || "Login failed.");
        }

        if (result.payload.requires_verification || (result.payload.data && result.payload.data.requires_verification)) {
          enterVerificationMode(result.payload, username);
          return;
        }

        if (result.payload.authenticated) {
          window.location.replace(getNextUrl());
          return;
        }

        throw new Error("Login response did not include verification or authenticated session.");
      });
  }

  function submitVerificationCode() {
    var codeInput = getVerificationInput();
    var code = codeInput ? codeInput.value.trim() : "";

    if (!verificationState.challengeToken) {
      setMessage("Verification session is missing. Please login again.");
      return Promise.resolve();
    }

    if (!/^\d{6}$/.test(code)) {
      setMessage("Enter the 6-digit verification code.");
      if (codeInput) codeInput.focus();
      return Promise.resolve();
    }

    setLoading(true);
    setMessage("");

    return fetch("/api/auth/verify-login", {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        challenge_token: verificationState.challengeToken,
        code: code
      })
    })
      .then(function (response) {
        return response.json().catch(function () {
          return {};
        }).then(function (payload) {
          return { ok: response.ok, status: response.status, payload: payload };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.payload || !result.payload.success) {
          throw new Error((result.payload && (result.payload.message || result.payload.error)) || "Verification failed.");
        }

        window.location.replace(getNextUrl());
      });
  }

  if (!form) {
    return;
  }

  bindRestartButton();
  checkExistingSession();

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var request = verificationState.active
      ? submitVerificationCode()
      : submitPasswordLogin();

    request
      .catch(function (error) {
        setMessage(error.message || "Login failed.");
      })
      .finally(function () {
        setLoading(false);
      });
  });
})();