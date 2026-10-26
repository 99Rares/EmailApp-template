document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".alert-dismissible").forEach((alertElement) => {
    window.setTimeout(() => {
      if (!alertElement.isConnected) {
        return;
      }

      if (window.bootstrap?.Alert) {
        window.bootstrap.Alert.getOrCreateInstance(alertElement).close();
        return;
      }

      alertElement.remove();
    }, 10000);
  });
});
