(function () {
  "use strict";

  var form = document.getElementById("resetPasswordForm");
  var button = document.getElementById("resetButton");
  var message = document.getElementById("resetMessage");

  function getToken() {
    var params = new URLSearchParams(window.location.search);
    return params.get("token") || "";
  }

  function setMessage(value) {
    if (message) {
      message.textContent = value || "";
    }
  }

  function setLoading(isLoading) {
    if (!button) {
      return;
    }

    button.disabled = isLoading;
    button.textContent = isLoading ? "Resetting..." : "Reset Password";
  }

  if (!form) {
    return;
  }

  if (!getToken()) {
    setMessage("Reset token is missing. Request a new reset link.");
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var token = getToken();
    var newPasswordInput = document.getElementById("newPassword");
    var confirmPasswordInput = document.getElementById("confirmPassword");

    var newPassword = newPasswordInput ? newPasswordInput.value : "";
    var confirmPassword = confirmPasswordInput ? confirmPasswordInput.value : "";

    if (!token) {
      setMessage("Reset token is missing.");
      return;
    }

    if (!newPassword || newPassword.length < 10) {
      setMessage("New password must be at least 10 characters.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setMessage("Password confirmation does not match.");
      return;
    }

    setLoading(true);
    setMessage("");

    fetch("/api/auth/reset-password", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        token: token,
        new_password: newPassword
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
          throw new Error((result.payload && result.payload.message) || "Failed to reset password.");
        }

        setMessage("Password reset successful. Redirecting to login...");

        window.setTimeout(function () {
          window.location.href = "/admin/login.html";
        }, 1200);
      })
      .catch(function (error) {
        setMessage(error.message || "Failed to reset password.");
      })
      .finally(function () {
        setLoading(false);
      });
  });
})();