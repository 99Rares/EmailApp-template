(function () {
  const storageKey = "emailapp-season";
  const labels = {
    auto: "Automatic",
    christmas: "Christmas",
    easter: "Easter",
    off: "Off",
  };

  function getPreference() {
    try {
      const saved = localStorage.getItem(storageKey);
      return Object.hasOwn(labels, saved) ? saved : "auto";
    } catch (error) {
      return "auto";
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    const preference = getPreference();
    document.querySelectorAll(".season-label").forEach((label) => {
      label.textContent = labels[preference];
    });

    document.querySelectorAll("[data-season]").forEach((button) => {
      const isActive = button.dataset.season === preference;
      button.classList.toggle("active", isActive);
      button.setAttribute("aria-pressed", String(isActive));

      button.addEventListener("click", () => {
        try {
          localStorage.setItem(storageKey, button.dataset.season);
        } catch (error) {
          return;
        }
        window.location.reload();
      });
    });
  });
})();
