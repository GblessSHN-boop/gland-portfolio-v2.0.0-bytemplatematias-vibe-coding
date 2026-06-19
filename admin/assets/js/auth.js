(function () {
  "use strict";

  var form = document.getElementById("adminLoginForm");
  var message = document.getElementById("loginMessage");
  var button = document.getElementById("loginButton");

  function getNextUrl() {
    var params = new URLSearchParams(window.location.search);
    var next = params.get("next");

    if (next && next.indexOf("/admin/") === 0 && next.indexOf("/admin/login.html") !== 0) {
      return next;
    }

    return "/admin/dashboard.html";
  }

  function setMessage(value) {
    if (message) {
      message.textContent = value || "";
    }
  }

  function setLoading(isLoading) {
    if (button) {
      button.disabled = isLoading;
      button.textContent = isLoading ? "Logging in..." : "Login";
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
        if (!response.ok) {
          return null;
        }

        return response.json();
      })
      .then(function (payload) {
        if (payload && payload.authenticated) {
          window.location.href = getNextUrl();
        }
      })
      .catch(function () {});
  }

  if (!form) {
    return;
  }

  checkExistingSession();

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var usernameInput = document.getElementById("username");
    var passwordInput = document.getElementById("password");

    var username = usernameInput ? usernameInput.value.trim() : "";
    var password = passwordInput ? passwordInput.value : "";

    if (!username || !password) {
      setMessage("Username and password are required.");
      return;
    }

    setLoading(true);
    setMessage("");

    fetch("/api/auth/login", {
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
          return {
            ok: response.ok,
            payload: payload
          };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.payload || !result.payload.success) {
          throw new Error((result.payload && result.payload.message) || "Login failed.");
        }

        window.location.href = getNextUrl();
      })
      .catch(function (error) {
        setMessage(error.message || "Login failed.");
      })
      .finally(function () {
        setLoading(false);
      });
  });
})();