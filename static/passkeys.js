(() => {
  const b64u = {
    toBuf: (s) => {
      const p = s.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (s.length % 4)) % 4);
      return Uint8Array.from(atob(p), (c) => c.charCodeAt(0)).buffer;
    },
    fromBuf: (b) =>
      btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""),
  };
  const supported = () => !!window.PublicKeyCredential && !!navigator.credentials;
  const csrf = () => document.querySelector('meta[name="csrf-token"]')?.content || "";

  async function api(method, url, body) {
    const res = await fetch(url, {
      method,
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf(), Accept: "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || data.message || `Request failed (${res.status})`);
    }
    return data;
  }

  async function createPasskey(options) {
    const cred = await navigator.credentials.create({
      publicKey: {
        ...options,
        challenge: b64u.toBuf(options.challenge),
        user: { ...options.user, id: b64u.toBuf(options.user.id) },
        excludeCredentials: (options.excludeCredentials || []).map((c) => ({ ...c, id: b64u.toBuf(c.id) })),
      },
    });
    return {
      id: cred.id,
      rawId: b64u.fromBuf(cred.rawId),
      type: cred.type,
      response: {
        clientDataJSON: b64u.fromBuf(cred.response.clientDataJSON),
        attestationObject: b64u.fromBuf(cred.response.attestationObject),
        transports: cred.response.getTransports ? cred.response.getTransports() : [],
      },
      clientExtensionResults: cred.getClientExtensionResults ? cred.getClientExtensionResults() : {},
      authenticatorAttachment: cred.authenticatorAttachment || undefined,
    };
  }

  async function getPasskey(options) {
    const cred = await navigator.credentials.get({
      publicKey: {
        ...options,
        challenge: b64u.toBuf(options.challenge),
        allowCredentials: (options.allowCredentials || []).map((c) => ({ ...c, id: b64u.toBuf(c.id) })),
      },
    });
    return {
      id: cred.id,
      rawId: b64u.fromBuf(cred.rawId),
      type: cred.type,
      response: {
        clientDataJSON: b64u.fromBuf(cred.response.clientDataJSON),
        authenticatorData: b64u.fromBuf(cred.response.authenticatorData),
        signature: b64u.fromBuf(cred.response.signature),
        userHandle: cred.response.userHandle ? b64u.fromBuf(cred.response.userHandle) : undefined,
      },
      clientExtensionResults: cred.getClientExtensionResults ? cred.getClientExtensionResults() : {},
      authenticatorAttachment: cred.authenticatorAttachment || undefined,
    };
  }

  function friendly(err) {
    return err && err.name === "NotAllowedError" ? "Cancelled or timed out." : err.message || "Something went wrong.";
  }

  function deviceName() {
    const ua = navigator.userAgent;
    const os = /iPhone/.test(ua) ? "iPhone" : /iPad/.test(ua) ? "iPad" : /Android/.test(ua) ? "Android"
      : /Mac/.test(ua) ? "Mac" : /Windows/.test(ua) ? "Windows" : /Linux/.test(ua) ? "Linux" : "Device";
    const browser = /Edg\//.test(ua) ? "Edge" : /Firefox\//.test(ua) ? "Firefox"
      : /Chrome\//.test(ua) ? "Chrome" : /Safari\//.test(ua) ? "Safari" : "";
    return browser ? `${os} · ${browser}` : os;
  }

  // ---- login page ----
  const loginBtn = document.getElementById("passkeyLogin");
  if (loginBtn) {
    const errorBox = document.getElementById("passkeyError");
    if (!supported()) {
      document.getElementById("passkeyBlock")?.classList.add("d-none");
    }
    loginBtn.addEventListener("click", async () => {
      errorBox.classList.add("d-none");
      loginBtn.disabled = true;
      try {
        const options = await api("POST", "/passkey/login/options");
        const credential = await getPasskey(options);
        await api("POST", "/passkey/login/verify", {
          credential,
          remember: document.getElementById("remember")?.checked || false,
        });
        window.location.href = "/";
      } catch (err) {
        errorBox.textContent = friendly(err);
        errorBox.classList.remove("d-none");
        loginBtn.disabled = false;
      }
    });
  }

  // ---- manage passkeys (index page modal) ----
  const modal = document.getElementById("passkeyModal");
  if (modal) {
    // Keep the modal out of any glass/transformed container so its backdrop does not cover it.
    document.body.append(modal);
    const list = document.getElementById("passkeyList");
    const status = document.getElementById("passkeyStatus");
    const addBtn = document.getElementById("passkeyAdd");
    const fmt = (t) => (t ? new Date(t * 1000).toLocaleDateString() : "never");
    const say = (msg, bad) => {
      status.textContent = msg;
      status.className = `small mt-2 ${bad ? "text-danger" : "text-success"}`;
    };

    async function refresh() {
      const data = await api("GET", "/passkeys");
      list.replaceChildren();
      if (!data.passkeys.length) {
        const li = document.createElement("li");
        li.className = "list-group-item text-body-secondary";
        li.textContent = "No passkeys yet.";
        list.append(li);
      }
      for (const p of data.passkeys) {
        const li = document.createElement("li");
        li.className = "list-group-item d-flex justify-content-between align-items-center gap-2";
        const info = document.createElement("div");
        const name = document.createElement("div");
        name.textContent = p.label;
        const meta = document.createElement("small");
        meta.className = "text-body-secondary";
        meta.textContent = `Added ${fmt(p.created_at)} · last used ${fmt(p.last_used)}`;
        info.append(name, meta);
        const del = document.createElement("button");
        del.type = "button";
        del.className = "btn btn-sm btn-outline-danger";
        del.textContent = "Remove";
        del.addEventListener("click", async () => {
          if (!confirm(`Remove the passkey "${p.label}"?`)) return;
          try {
            await api("DELETE", `/passkeys/${encodeURIComponent(p.credential_id)}`);
            await refresh();
          } catch (err) {
            say(friendly(err), true);
          }
        });
        li.append(info, del);
        list.append(li);
      }
      addBtn.disabled = !data.enabled || data.passkeys.length >= data.max;
      if (!data.enabled) say("Passkeys are not enabled on this server (PASSKEY_ORIGINS is not set).", true);
    }

    modal.addEventListener("show.bs.modal", () => {
      status.textContent = "";
      if (!supported()) {
        addBtn.disabled = true;
        say("This browser does not support passkeys.", true);
        return;
      }
      refresh().catch((err) => say(friendly(err), true));
    });

    addBtn.addEventListener("click", async () => {
      addBtn.disabled = true;
      try {
        const options = await api("POST", "/passkeys/options");
        const credential = await createPasskey(options);
        const label = prompt("Name this passkey", deviceName());
        if (label === null) return;
        await api("POST", "/passkeys/verify", { credential, label });
        say("Passkey added.", false);
      } catch (err) {
        say(friendly(err), true);
      } finally {
        await refresh().catch(() => {});
      }
    });
  }
})();
