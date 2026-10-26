(function () {
  const dayInMilliseconds = 24 * 60 * 60 * 1000;

  function getOrthodoxEaster(year) {
    const a = year % 4;
    const b = year % 7;
    const c = year % 19;
    const d = (19 * c + 15) % 30;
    const e = (2 * a + 4 * b - d + 34) % 7;
    const value = d + e + 114;
    const month = Math.floor(value / 31);
    const day = (value % 31) + 1;
    const gregorianOffset = Math.floor(year / 100) - Math.floor(year / 400) - 2;

    return new Date(Date.UTC(year, month - 1, day + gregorianOffset));
  }

  function isEasterSeason(date) {
    const today = Date.UTC(date.getFullYear(), date.getMonth(), date.getDate());
    const easter = getOrthodoxEaster(date.getFullYear()).getTime();
    const start = easter - 10 * dayInMilliseconds;
    const end = easter + 7 * dayInMilliseconds;
    return today >= start && today <= end;
  }

  function getSeasonPreference() {
    try {
      const saved = localStorage.getItem("emailapp-season");
      return ["auto", "christmas", "easter", "off"].includes(saved) ? saved : "auto";
    } catch (error) {
      return "auto";
    }
  }

  function getEggCount() {
    if (window.innerWidth < 576) {
      return 6;
    }
    if (window.innerWidth < 992) {
      return 10;
    }
    if (window.innerWidth < 1400) {
      return 14;
    }
    return 20;
  }

  function createEgg() {
    const egg = document.createElement("img");
    egg.className = "floating-easter-egg";
    egg.src = "/static/easter-egg.png";
    egg.alt = "";
    return egg;
  }

  function syncEggCount(eggLayer) {
    const eggCount = getEggCount();

    while (eggLayer.children.length > eggCount) {
      eggLayer.lastElementChild.remove();
    }

    while (eggLayer.children.length < eggCount) {
      eggLayer.appendChild(createEgg());
    }
  }

  const preference = getSeasonPreference();
  const easterEnabled =
    preference === "easter" ||
    (preference === "auto" && isEasterSeason(new Date()));

  if (!easterEnabled) {
    return;
  }

  // A manually enabled Christmas preview takes precedence over Easter styling.
  if (document.documentElement.classList.contains("christmas-theme")) {
    return;
  }

  document.documentElement.classList.add("easter-theme");

  document.addEventListener("DOMContentLoaded", () => {
    ["left", "right"].forEach((side) => {
      const rabbit = document.createElement("img");
      rabbit.src = "/static/easter-rabbit.png";
      rabbit.alt = "";
      rabbit.className = `easter-rabbit easter-rabbit-${side}`;
      rabbit.setAttribute("aria-hidden", "true");
      document.body.appendChild(rabbit);
    });

    const eggLayer = document.createElement("div");
    eggLayer.className = "easter-eggs";
    eggLayer.setAttribute("aria-hidden", "true");

    syncEggCount(eggLayer);
    document.body.appendChild(eggLayer);

    let resizeFrame = null;
    window.addEventListener(
      "resize",
      () => {
        if (resizeFrame !== null) {
          cancelAnimationFrame(resizeFrame);
        }
        resizeFrame = requestAnimationFrame(() => {
          syncEggCount(eggLayer);
          resizeFrame = null;
        });
      },
      { passive: true },
    );
  });
})();
