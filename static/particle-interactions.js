(function () {
  let animationFrame = null;
  let pointer = null;

  function removeHitParticles() {
    animationFrame = null;
    if (!pointer) {
      return;
    }

    document.querySelectorAll(".snowflake, .floating-easter-egg").forEach((particle) => {
      if (particle.classList.contains("particle-hit")) {
        return;
      }

      const bounds = particle.getBoundingClientRect();
      const padding = pointer.isTouch ? 18 : 6;
      const isHit =
        pointer.x >= bounds.left - padding &&
        pointer.x <= bounds.right + padding &&
        pointer.y >= bounds.top - padding &&
        pointer.y <= bounds.bottom + padding;

      if (isHit) {
        particle.classList.add("particle-hit");
        window.setTimeout(() => particle.remove(), 180);
      }
    });
  }

  function handlePointer(event) {
    pointer = {
      x: event.clientX,
      y: event.clientY,
      isTouch: event.pointerType === "touch",
    };

    if (animationFrame === null) {
      animationFrame = window.requestAnimationFrame(removeHitParticles);
    }
  }

  document.addEventListener("pointermove", handlePointer, { passive: true });
  document.addEventListener("pointerdown", handlePointer, { passive: true });
})();
