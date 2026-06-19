(function () {
  "use strict";

  var form = document.getElementById("forgotPasswordForm");
  var button = document.getElementById("forgotButton");
  var message = document.getElementById("forgotMessage");

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

  function setLoading(isLoading) {
    if (!button) {
      return;
    }

    button.disabled = isLoading;
    button.textContent = isLoading ? "Sending..." : "Send Reset Link";
  }

  if (!form) {
    return;
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var identifierInput = document.getElementById("identifier");
    var identifier = identifierInput ? identifierInput.value.trim() : "";

    if (!identifier) {
      setMessage("Username or email is required.");
      return;
    }

    setLoading(true);
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
            payload: payload
          };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.payload || !result.payload.success) {
          throw new Error((result.payload && result.payload.message) || "Failed to request password reset.");
        }

        var debugUrl = result.payload.data && result.payload.data.debug_reset_url;

        if (debugUrl) {
          setMessage(
            "Reset link generated. Local debug link: <a href=\"" + debugUrl + "\">Open reset link</a>",
            true
          );
          return;
        }

        setMessage("If the admin account exists, a reset link has been sent to the registered Gmail account.");
      })
      .catch(function (error) {
        setMessage(error.message || "Failed to request password reset.");
      })
      .finally(function () {
        setLoading(false);
      });
  });
})();