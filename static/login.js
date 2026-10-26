document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("loginForm");
  if (!form) {
    return;
  }

  const passwordInput = document.getElementById("password");
  const toggle = form.querySelector(".password-toggle");
  const submit = form.querySelector(".login-submit");
  const spinner = submit.querySelector(".spinner-border");
  const label = submit.querySelector(".login-submit-label");

  toggle.addEventListener("click", () => {
    const show = passwordInput.type === "password";
    passwordInput.type = show ? "text" : "password";
    toggle.setAttribute("aria-pressed", String(show));
    toggle.setAttribute("aria-label", show ? "Hide password" : "Show password");
    toggle.querySelector("i").className = show ? "bi bi-eye-slash-fill" : "bi bi-eye-fill";
    passwordInput.focus();
  });

  function setSubmitting(submitting) {
    submit.disabled = submitting;
    submit.setAttribute("aria-busy", String(submitting));
    spinner.classList.toggle("d-none", !submitting);
    label.textContent = submitting ? "Signing in\u2026" : "Sign in";
  }

  form.addEventListener("submit", (event) => {
    if (!form.checkValidity()) {
      event.preventDefault();
      form.reportValidity();
      return;
    }
    setSubmitting(true);
  });

  // Restore the button when the page returns from the back/forward cache.
  window.addEventListener("pageshow", () => setSubmitting(false));

  [form.elements.username, passwordInput].forEach((input) => {
    input.addEventListener("input", () => input.classList.remove("is-invalid"));
  });
});
