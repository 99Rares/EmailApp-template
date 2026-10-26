function setLoadingSpinnerVisible(visible) {
  const overlay = document.getElementById("loadingOverlay");
  if (!overlay) {
    return;
  }
  overlay.classList.toggle("is-visible", visible);
  overlay.setAttribute("aria-hidden", String(!visible));
}

window.addEventListener("pageshow", () => {
  setLoadingSpinnerVisible(false);
});

function updateRuleFormRequirements(actionType) {
  const generatedEmail = document.getElementById("generated_email");
  const destinationEmail = document.getElementById("destination_email");

  if (actionType === "drop") {
    generatedEmail.required = true;
    destinationEmail.required = false;
  } else {
    generatedEmail.required = false;
    destinationEmail.required = true;
  }
}

function populateRuleForm(row) {
  document.querySelectorAll("#emailTable tbody tr").forEach((item) => {
    item.classList.remove("selected");
  });
  row.classList.add("selected");

  const actionType = row.dataset.actionType || "forward";
  document.getElementById("generated_email").value = row.dataset.generatedEmail || "";
  document.getElementById("app_name").value = row.dataset.serviceName || "";
  document.getElementById("action_type").value = actionType;

  const destination = row.dataset.destinationEmail || "";
  const destinationSelect = document.getElementById("destination_email");
  destinationSelect.value = actionType === "drop" ? "" : destination;
  updateRuleFormRequirements(actionType);
  document.getElementById("editor-title").textContent = "Edit routing rule";
  document.getElementById("saveRule").textContent = "Save changes";
  document.getElementById("cancelEdit").classList.remove("d-none");
  document.getElementById("ruleForm").scrollIntoView({ behavior: "instant", block: "center" });
  document.getElementById("generated_email").focus({ preventScroll: true });
}

async function copyEmail(row) {
  const text = row.dataset.generatedEmail || "";
  const button = row.querySelector(".copy-email-btn");
  try {
    await navigator.clipboard.writeText(text);
  } catch (error) {
    const area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
  const icon = button.querySelector("i");
  icon.className = "bi bi-check2";
  clearTimeout(button.resetTimer);
  button.resetTimer = setTimeout(() => { icon.className = "bi bi-copy"; }, 1200);
}

document.addEventListener("DOMContentLoaded", () => {
  const actionType = document.getElementById("action_type");
  actionType.addEventListener("change", () => updateRuleFormRequirements(actionType.value));
  updateRuleFormRequirements(actionType.value);

  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!form.checkValidity()) {
        event.preventDefault();
        form.reportValidity();
        return;
      }
      setLoadingSpinnerVisible(true);
    });
  });

  document.getElementById("cancelEdit").addEventListener("click", () => {
    document.getElementById("ruleForm").reset();
    updateRuleFormRequirements(actionType.value);
    document.getElementById("editor-title").textContent = "Add a routing rule";
    document.getElementById("saveRule").textContent = "Add rule";
    document.getElementById("cancelEdit").classList.add("d-none");
    document.querySelectorAll("tr.selected").forEach(row => row.classList.remove("selected"));
  });

  document.querySelectorAll("#emailTable tbody tr").forEach((row) => {
    row.querySelector(".edit-rule").addEventListener("click", () => populateRuleForm(row));
    row.querySelector(".copy-email").addEventListener("click", () => copyEmail(row));
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("ruleSearch");
  if (!input) {
    return;
  }
  const rows = Array.from(document.querySelectorAll("#emailTable tbody tr"));
  const count = document.getElementById("ruleCount");
  const empty = document.getElementById("searchEmpty");
  const haystacks = rows.map((row) =>
    [...row.querySelectorAll("td:not(.rule-actions)")].map((td) => td.textContent).join(" ").toLowerCase()
  );

  const applySearch = () => {
    const terms = input.value.toLowerCase().split(/\s+/).filter(Boolean);
    let shown = 0;
    rows.forEach((row, i) => {
      const match = terms.every((term) => haystacks[i].includes(term));
      row.classList.toggle("d-none", !match);
      if (match) {
        shown += 1;
      }
    });
    count.textContent = terms.length ? `${shown} / ${rows.length}` : count.dataset.total;
    empty.classList.toggle("d-none", shown > 0);
  };

  input.addEventListener("input", applySearch);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && input.value) {
      input.value = "";
      applySearch();
    }
  });
  applySearch();
});
