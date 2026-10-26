(function () {
  const themeStorageKey = "emailapp-theme";
  const styleStorageKey = "emailapp-ui-style";
  const styleDetails = {
    liquid: { label: "Standard glass", icon: "bi bi-droplet-fill" },
    extreme: { label: "Vivid glass", icon: "bi bi-radioactive" },
    default: { label: "Solid appearance", icon: "bi bi-square" },
  };
  let theme = "dark";
  let uiStyle = "liquid";

  try {
    const savedTheme = localStorage.getItem(themeStorageKey);
    const savedStyle = localStorage.getItem(styleStorageKey);
    if (savedTheme === "light" || savedTheme === "dark") {
      theme = savedTheme;
    }
    if (Object.prototype.hasOwnProperty.call(styleDetails, savedStyle)) {
      uiStyle = savedStyle;
    }
  } catch (error) {
    // Keep the defaults when browser storage is unavailable.
  }

  document.documentElement.setAttribute("data-bs-theme", theme);
  document.documentElement.setAttribute("data-ui-style", uiStyle);

  function updateControls() {
    const isDark = document.documentElement.getAttribute("data-bs-theme") === "dark";
    const currentStyle = document.documentElement.getAttribute("data-ui-style");
    const details = styleDetails[currentStyle] || styleDetails.liquid;

    document.querySelectorAll(".theme-toggle").forEach((button) => {
      button.setAttribute("aria-label", `Switch to ${isDark ? "light" : "dark"} mode`);
      button.querySelector(".theme-label").textContent = isDark ? "Light mode" : "Dark mode";
      button.querySelector("i").className = isDark ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
    });

    document.querySelectorAll(".appearance-toggle").forEach((button) => {
      button.setAttribute("aria-label", `Appearance: ${details.label}`);
      button.querySelector(".style-label").textContent = details.label;
      button.querySelector("i").className = details.icon;
    });

    document.querySelectorAll("[data-ui-style-option]").forEach((button) => {
      button.classList.toggle("active", button.dataset.uiStyleOption === currentStyle);
      button.setAttribute("aria-current", button.dataset.uiStyleOption === currentStyle ? "true" : "false");
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    updateControls();

    document.querySelectorAll(".theme-toggle").forEach((button) => {
      button.addEventListener("click", () => {
        const currentTheme = document.documentElement.getAttribute("data-bs-theme");
        const nextTheme = currentTheme === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-bs-theme", nextTheme);
        try {
          localStorage.setItem(themeStorageKey, nextTheme);
        } catch (error) {
          // The theme still works for this page when storage is unavailable.
        }
        updateControls();
      });
    });

    document.querySelectorAll("[data-ui-style-option]").forEach((button) => {
      button.addEventListener("click", () => {
        const nextStyle = button.dataset.uiStyleOption;
        document.documentElement.setAttribute("data-ui-style", nextStyle);
        try {
          localStorage.setItem(styleStorageKey, nextStyle);
        } catch (error) {
          // The appearance still works for this page when storage is unavailable.
        }
        updateControls();
      });
    });
  });
})();
