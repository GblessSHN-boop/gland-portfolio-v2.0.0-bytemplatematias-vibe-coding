(function () {
  "use strict";

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

  function getVerificationInput() {
    return document.getElementById("verificationCode");
  }

  function ensureVerificationStep() {
    if (!form || document.getElementById("loginVerificationStep")) {
      return;
    }

    var wrapper = document.createElement("div");
    wrapper.id = "loginVerificationStep";
    wrapper.className = "verification-step";
    wrapper.hidden = true;

    wrapper.innerHTML = [
      '<label for="verificationCode">6-Digit Verification Code</label>',
      '<input id="verificationCode" name="verificationCode" type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="6" pattern="[0-9]{6}" placeholder="000000" />',
      '<p class="verification-hint" id="verificationHint">Enter the code sent to your admin email.</p>',
      '<button class="secondary-button" id="restartLoginButton" type="button">Use another account</button>'
    ].join("");

    var passwordInput = document.getElementById("password");

    if (passwordInput && passwordInput.parentNode) {
      passwordInput.insertAdjacentElement("afterend", wrapper);
    } else {
      form.insertBefore(wrapper, button);
    }

    var restartButton = document.getElementById("restartLoginButton");
    if (restartButton) {
      restartButton.addEventListener("click", function () {
        verificationState.active = false;
        verificationState.challengeToken = "";
        verificationState.username = "";

        var usernameInput = document.getElementById("username");
        var passwordInput = document.getElementById("password");
        var codeInput = getVerificationInput();

        if (usernameInput) usernameInput.disabled = false;
        if (passwordInput) {
          passwordInput.disabled = false;
          passwordInput.value = "";
        }
        if (codeInput) codeInput.value = "";

        wrapper.hidden = true;
        setMessage("");
        setLoading(false);
      });
    }
  }

  function enterVerificationMode(payload, username) {
    ensureVerificationStep();

    var data = (payload && payload.data) || {};
    var wrapper = document.getElementById("loginVerificationStep");
    var hint = document.getElementById("verificationHint");
    var usernameInput = document.getElementById("username");
    var passwordInput = document.getElementById("password");
    var codeInput = getVerificationInput();

    verificationState.active = true;
    verificationState.challengeToken = data.challenge_token || "";
    verificationState.username = username || "";

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
          window.location.href = getNextUrl();
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
        return response.json().then(function (payload) {
          return { ok: response.ok, payload: payload };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.payload || !result.payload.success) {
          throw new Error((result.payload && result.payload.message) || "Login failed.");
        }

        if (result.payload.requires_verification || (result.payload.data && result.payload.data.requires_verification)) {
          enterVerificationMode(result.payload, username);
          return;
        }

        window.location.href = getNextUrl();
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
        return response.json().then(function (payload) {
          return { ok: response.ok, payload: payload };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.payload || !result.payload.success) {
          throw new Error((result.payload && result.payload.message) || "Verification failed.");
        }

        window.location.href = getNextUrl();
      });
  }

  if (!form) {
    return;
  }

  ensureVerificationStep();
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