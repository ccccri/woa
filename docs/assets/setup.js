// WOA setup page: Login with Amazon (implicit grant) + calls to the WOA API.
(function () {
  const cfg = window.WOA_CONFIG || {};
  const { t } = window.WOA_I18N;
  const TOKEN_KEY = "woa-token";
  const $ = (id) => document.getElementById(id);
  const configured = cfg.lwaClientId && !cfg.lwaClientId.includes("REPLACE_ME") &&
    cfg.apiUrl && !cfg.apiUrl.includes("REPLACE_ME");

  let state = { devices: [], linked: false };

  // --- Token storage (session only, cleared when the tab closes) ---------------
  function saveToken(token, expiresIn) {
    const expiresAt = Date.now() + (Number(expiresIn) || 3600) * 1000 - 60000;
    sessionStorage.setItem(TOKEN_KEY, JSON.stringify({ token, expiresAt }));
  }
  function getToken() {
    try {
      const saved = JSON.parse(sessionStorage.getItem(TOKEN_KEY));
      if (saved && saved.expiresAt > Date.now()) return saved.token;
    } catch (_) { /* ignore */ }
    sessionStorage.removeItem(TOKEN_KEY);
    return null;
  }
  function signOut() {
    sessionStorage.removeItem(TOKEN_KEY);
    if (window.amazon) amazon.Login.logout();
    show(false);
  }

  // --- Login with Amazon SDK --------------------------------------------------
  window.onAmazonLoginReady = function () {
    amazon.Login.setClientId(cfg.lwaClientId);
  };
  function loadSdk() {
    const s = document.createElement("script");
    s.async = true;
    s.id = "amazon-login-sdk";
    s.src = "https://assets.loginwithamazon.com/sdk/na/login1.js";
    $("amazon-root").appendChild(s);
  }
  function signIn() {
    if (!window.amazon) return setMsg(t("genericError"), "err");
    amazon.Login.authorize(
      { scope: "profile:user_id", response_type: "token", popup: true },
      (resp) => {
        if (resp.error || !resp.access_token) return setMsg(t("genericError"), "err");
        saveToken(resp.access_token, resp.expires_in);
        refresh();
      }
    );
  }

  // --- API ---------------------------------------------------------------------
  async function api(method, path, body) {
    const token = getToken();
    if (!token) { show(false); throw new Error(t("sessionExpired")); }
    const resp = await fetch(cfg.apiUrl + path, {
      method,
      headers: Object.assign({ Authorization: "Bearer " + token },
        body ? { "Content-Type": "application/json" } : {}),
      body: body ? JSON.stringify(body) : undefined,
    });
    let data = {};
    try { data = await resp.json(); } catch (_) { /* empty body */ }
    if (resp.status === 401) { signOut(); throw new Error(t("sessionExpired")); }
    if (!resp.ok) throw new Error(data.error || t("genericError"));
    return data;
  }

  // --- UI ----------------------------------------------------------------------
  function setMsg(text, kind) {
    const el = $("msg");
    el.textContent = text || "";
    el.className = "msg" + (kind ? " " + kind : "");
  }

  function show(signedIn) {
    $("signed-in").hidden = !signedIn;
    $("signed-out").hidden = signedIn;
  }

  function render() {
    const status = $("link-status");
    status.textContent = "";
    const badge = document.createElement("span");
    badge.className = "badge " + (state.linked ? "ok" : "warn");
    badge.textContent = state.linked ? t("linked") : t("notLinked");
    status.appendChild(badge);
    $("link-help").hidden = state.linked;

    const list = $("devices");
    list.textContent = "";
    $("no-devices").hidden = state.devices.length > 0;
    for (const d of state.devices) {
      const li = document.createElement("li");
      const text = document.createElement("div");
      const name = document.createElement("div");
      name.className = "name";
      name.textContent = d.name;
      const mac = document.createElement("div");
      mac.className = "mac";
      mac.textContent = d.mac.replaceAll("-", ":");
      text.append(name, mac);
      const del = document.createElement("button");
      del.className = "btn secondary";
      del.textContent = t("remove");
      del.addEventListener("click", () => removeDevice(d));
      li.append(text, del);
      list.appendChild(li);
    }
  }

  async function refresh() {
    if (!getToken()) return show(false);
    show(true);
    try {
      const me = await api("GET", "/api/me");
      state = { devices: me.devices, linked: me.linked };
      render();
    } catch (err) {
      setMsg(err.message, "err");
    }
  }

  async function addDevice(ev) {
    ev.preventDefault();
    const form = ev.target;
    const button = form.querySelector("button");
    button.disabled = true;
    setMsg("");
    try {
      const name = $("name").value.trim();
      const res = await api("POST", "/api/devices", { name, mac: $("mac").value });
      form.reset();
      setMsg(res.synced ? t("added", { name: res.device.name }) : t("addedDiscover"), "ok");
      await refresh();
    } catch (err) {
      setMsg(err.message, "err");
    } finally {
      button.disabled = false;
    }
  }

  async function removeDevice(d) {
    if (!confirm(t("confirmRemove", { name: d.name }))) return;
    try {
      const res = await api("DELETE", "/api/devices/" + encodeURIComponent(d.id));
      setMsg(res.synced ? t("removed") : t("removedDiscover"), "ok");
      await refresh();
    } catch (err) {
      setMsg(err.message, "err");
    }
  }

  async function deleteAll() {
    if (!confirm(t("confirmDeleteAll"))) return;
    try {
      await api("DELETE", "/api/me");
      signOut();
      alert(t("deletedAll"));
    } catch (err) {
      setMsg(err.message, "err");
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (!configured) {
      $("config-error").hidden = false;
      $("sign-in").disabled = true;
      return;
    }
    loadSdk();
    $("sign-in").addEventListener("click", signIn);
    $("sign-out").addEventListener("click", signOut);
    $("delete-all").addEventListener("click", deleteAll);
    $("add-form").addEventListener("submit", addDevice);
    document.addEventListener("woa-lang", render);
    refresh();
  });
})();
