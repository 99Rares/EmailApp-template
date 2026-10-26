(function () {
  function isChristmasSeason(date) {
    const month = date.getMonth();
    return month === 11 || (month === 0 && date.getDate() <= 6);
  }

  function getSeasonPreference() {
    try {
      const saved = localStorage.getItem("emailapp-season");
      return ["auto", "christmas", "easter", "off"].includes(saved) ? saved : "auto";
    } catch (error) {
      return "auto";
    }
  }

  const preference = getSeasonPreference();
  const snowEnabled =
    preference === "christmas" ||
    (preference === "auto" && isChristmasSeason(new Date()));

  if (!snowEnabled) {
    return;
  }

  document.documentElement.classList.add("christmas-theme");

  document.addEventListener("DOMContentLoaded", () => {
    [
      ["/static/christmas-snowman.png", "left"],
      ["/static/christmas-tree.png", "right"],
    ].forEach(([source, side]) => {
      const decoration = document.createElement("img");
      decoration.src = source;
      decoration.alt = "";
      decoration.className = `christmas-corner-decoration christmas-decoration-${side}`;
      decoration.setAttribute("aria-hidden", "true");
      document.body.appendChild(decoration);
    });

    const snowfall = document.createElement("div");
    snowfall.className = "snowfall";
    snowfall.setAttribute("aria-hidden", "true");

    for (let index = 0; index < 48; index += 1) {
      const snowflake = document.createElement("span");
      snowflake.className = "snowflake";
      snowflake.textContent = "•";
      snowfall.appendChild(snowflake);
    }

    document.body.appendChild(snowfall);
  });
})();
