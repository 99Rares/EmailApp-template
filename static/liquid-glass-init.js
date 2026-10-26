(function () {
  "use strict";

  const instances = new Map();
  const root = document.documentElement;
  let activeStyle = null;

  function optionsFor(element, isExtreme) {
    if (element.matches(".btn")) {
      return isExtreme
        ? { scale: -125, chroma: 10, border: 0.1, mapBlur: 7, blur: 2, saturate: 2, fallbackBlur: 16 }
        : { scale: -62, chroma: 3, border: 0.14, mapBlur: 8, blur: 2, saturate: 1.45, fallbackBlur: 12 };
    }

    return isExtreme
      ? { scale: -165, chroma: 14, border: 0.055, mapBlur: 10, blur: 2, saturate: 2.1, fallbackBlur: 22 }
      : { scale: -86, chroma: 5, border: 0.08, mapBlur: 14, blur: 3, saturate: 1.55, fallbackBlur: 18 };
  }

  function targets(isExtreme) {
    const selector = isExtreme
      ? ".btn, .dropdown-menu, .alert, .table-responsive.card, .container .container, .card.mx-auto"
      : ".appearance-toggle, .theme-toggle, .dropdown > .btn, .card.mx-auto";
    return document.querySelectorAll(selector);
  }

  function disable() {
    instances.forEach((instance) => instance.destroy());
    instances.clear();
  }

  function enable(style) {
    if (typeof window.liquidGlass !== "function") {
      return;
    }

    const isExtreme = style === "extreme";
    targets(isExtreme).forEach((element) => {
      instances.set(element, window.liquidGlass(element, optionsFor(element, isExtreme)));
    });
  }

  function sync() {
    const style = root.getAttribute("data-ui-style");
    if (style === activeStyle) {
      return;
    }

    disable();
    activeStyle = style;
    if (style === "liquid" || style === "extreme") {
      enable(style);
    }
  }

  document.addEventListener("DOMContentLoaded", sync);

  new MutationObserver((mutations) => {
    if (mutations.some((mutation) => mutation.attributeName === "data-ui-style")) {
      sync();
    }
  }).observe(root, { attributes: true, attributeFilter: ["data-ui-style"] });
})();
