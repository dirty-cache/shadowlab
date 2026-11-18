/* Shadow Lab · Deployer — frontend
 * Vanilla JS, no dependencies (isolated lab network). */

"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const state = {
  token: localStorage.getItem("deployer.token") || "",
  authRequired: false,
  hosts: [],
  hostInfo: {},          // host_id -> daemon info (last known)
  hostId: localStorage.getItem("deployer.hostId") || "",
  overview: null,
  autoRefresh: true,
  job: null,             // current job object
  jobTimer: null,
  jobOffset: 0,
  logTimer: null,
  logProject: null,
};

/* ---------- api ---------- */

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (opts.body) headers["Content-Type"] = "application/json";
  if (state.token) headers["Authorization"] = "Bearer " + state.token;
  const res = await fetch("/api" + path, {
    method: opts.method || "GET",
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (res.status === 401) {
    state.authRequired = true;
    showLogin();
    throw new Error("unauthorized");
  }
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("json") ? await res.json() : await res.text();
  if (!res.ok) {
    const detail = typeof data === "object" && data ? data.detail : data;
    throw new Error(typeof detail === "string" ? detail : res.statusText);
  }
  return data;
}

/* ---------- utils ---------- */

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function toast(msg, kind = "info", actionLabel, onAction) {
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  const grow = document.createElement("span");
  grow.className = "grow";
  grow.textContent = msg;
  el.appendChild(grow);
  if (actionLabel) {
    const b = document.createElement("button");
    b.textContent = actionLabel;
    b.onclick = () => { onAction && onAction(); el.remove(); };
    el.appendChild(b);
  }
  $("#toasts").appendChild(el);
  setTimeout(() => el.remove(), 5000);
}

const ICONS = {
  cube: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z"/><path d="M4 7.5L12 12l8-4.5M12 12v9"/></svg>',
  gear: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3.2"/><path d="M12 2.5l1.2 2.6 2.8-.6 1 2.7 2.8.7-.6 2.8 2 2-2 2 .6 2.8-2.8.7-1 2.7-2.8-.6L12 21.5l-1.2-2.6-2.8.6-1-2.7-2.8-.7.6-2.8-2-2 2-2-.6-2.8 2.8-.7 1-2.7 2.8.6z"/></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 7h16M9 7V4h6v3M6.5 7l1 13h9l1-13"/></svg>',
  play: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7 4.5v15l13-7.5z"/></svg>',
  stop: '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="5.5" y="5.5" width="13" height="13" rx="2"/></svg>',
  restart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 11a8 8 0 1 0-2.34 6.34M20 5v6h-6"/></svg>',
  terminal: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 7l5 5-5 5M12 17h7"/></svg>',
  x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  caret: '<svg class="caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M6 9l6 6 6-6"/></svg>',
};

/* ---------- login ---------- */

function showLogin() {
  $("#app").classList.add("hidden");
  $("#login").classList.remove("hidden");
  $("#jobconsole").classList.add("hidden");
  setTimeout(() => $("#login-token").focus(), 50);
}

async function init() {
  let health;
  try {
    health = await api("/health");
  } catch (e) {
    if (state.authRequired) return;
    toast("Cannot reach the Deployer API: " + e.message, "error");
    return;
  }
  state.authRequired = health.auth;
  if (health.auth && !state.token) { showLogin(); return; }

  $("#login").classList.add("hidden");
  $("#app").classList.remove("hidden");
  $("#logout").classList.toggle("hidden", !state.token);
  $("#foot-version").textContent = `deployer ${health.version} · compose ${health.compose}`;

  try {
    const { hosts } = await api("/hosts");
    state.hosts = hosts;
    if (!state.hostId || !hosts.some((h) => h.id === state.hostId)) {
      state.hostId = hosts[0].id;
      localStorage.setItem("deployer.hostId", state.hostId);
    }
  } catch (e) {
    toast(e.message, "error");
    return;
  }
  renderHosts();
  await loadOverview();
  refreshHostDots();
  startAutoRefresh();
}

/* ---------- hosts ---------- */

function renderHosts() {
  const list = $("#host-list");
  list.innerHTML = "";
  $("#host-count").textContent = String(state.hosts.length);
  for (const h of state.hosts) {
    const info = state.hostInfo[h.id];
    const dotClass = info ? (info.ok ? "ok" : "err") : "";
    const item = document.createElement("button");
    item.className = "host-item" + (h.id === state.hostId ? " active" : "");
    item.dataset.id = h.id;
    item.title = h.description || h.address;
    item.innerHTML = `
      <span class="dot ${dotClass}"></span>
      <span class="host-body">
        <span class="host-name">${esc(h.name)}</span>
        <span class="host-addr">${esc(h.address)}</span>
      </span>
      <span class="host-actions">
        <button data-act="edit" title="Edit host">${ICONS.gear}</button>
        <button data-act="del" title="Remove host">${ICONS.trash}</button>
      </span>`;
    item.addEventListener("click", (ev) => {
      const act = ev.target.closest("button[data-act]");
      if (act) {
        ev.stopPropagation();
        if (act.dataset.act === "edit") openHostModal(h);
        else confirmRemoveHost(h);
        return;
      }
      selectHost(h.id);
    });
    list.appendChild(item);
  }
}

async function selectHost(hostId) {
  if (hostId === state.hostId && state.overview) return;
  state.hostId = hostId;
  localStorage.setItem("deployer.hostId", hostId);
  renderHosts();
  await loadOverview();
}

async function loadOverview() {
  if (!state.hosts.length) return;
  const host = state.hosts.find((h) => h.id === state.hostId);
  if (!host) return;
  try {
    state.overview = await api(`/overview?host_id=${encodeURIComponent(host.id)}`);
    state.hostInfo[host.id] = state.overview.info;
  } catch (e) {
    toast(e.message, "error");
    return;
  }
  renderHosts();
  renderOverview();
}

async function refreshHostDots() {
  // Ping hosts we have not seen recently (parallel, best effort).
  const stale = state.hosts.filter((h) => !state.hostInfo[h.id]);
  await Promise.all(stale.map(async (h) => {
    try {
      state.hostInfo[h.id] = await api(`/hosts/${encodeURIComponent(h.id)}/info`);
    } catch (e) {
      state.hostInfo[h.id] = { ok: false, error: e.message };
    }
  }));
  renderHosts();
}

/* ---------- overview ---------- */

function renderOverview() {
  const { host, info, projects } = state.overview;
  $("#tb-title").textContent = "Projects";
  const sub = $("#tb-sub");
  if (info.ok) {
    sub.textContent = `${host.name} · docker ${info.version} · ${info.containers_running ?? 0}/${info.containers ?? 0} containers`;
  } else {
    sub.textContent = `${host.name} · unreachable`;
  }

  const banner = $("#banner");
  if (!info.ok) {
    banner.classList.remove("hidden");
    banner.innerHTML = `⚠ Cannot reach the Docker daemon at <span class="muted">${esc(host.address)}</span> — ${esc(info.error || "unknown error")}`;
  } else {
    banner.classList.add("hidden");
  }

  const grid = $("#projects");
  grid.innerHTML = "";
  if (!projects.length) {
    grid.innerHTML = `
      <div class="empty">
        <div class="big">No compose projects found</div>
        <div>Add folders containing a <code>compose.yaml</code> to
        <code>${esc(state.overview && state.overview.host ? "the projects directory" : "the projects directory")}</code>
        and refresh.</div>
      </div>`;
    return;
  }
  for (const p of projects) grid.appendChild(projectCard(p));
}

function serviceState(p, svc) {
  const s = p.status[svc.name];
  if (!s) return { cls: "", label: "stopped" };
  if (s.state === "running") {
    if (s.health === "healthy") return { cls: "ok", label: "healthy" };
    if (s.health === "unhealthy") return { cls: "err", label: "unhealthy" };
    if (s.health === "starting") return { cls: "info", label: "starting" };
    return { cls: "ok", label: "running" };
  }
  if (s.state === "restarting") return { cls: "info", label: "restarting" };
  if (s.state === "paused") return { cls: "warn", label: "paused" };
  return { cls: "err", label: (s.state || "exited").toLowerCase() };
}

function projectCard(p) {
  const job = state.job;
  const busy = job && job.project === p.name && job.status === "running";
  const total = p.services.length;
  const up = p.services.filter((s) => {
    const st = p.status[s.name];
    return st && (st.state === "running" || st.state === "restarting");
  }).length;
  const down = p.services.filter((s) => {
    const st = p.status[s.name];
    return st && st.state !== "running" && st.state !== "restarting";
  }).length;

  let summary;
  if (!state.overview.info.ok) summary = '<span class="chip">—</span>';
  else if (total === 0) summary = '<span class="chip warn">no services parsed</span>';
  else if (up === total) summary = `<span class="chip ok">${total} up</span>`;
  else if (up > 0) summary = `<span class="chip warn">${up} up · ${down} down</span>`;
  else summary = down > 0
    ? '<span class="chip err">stopped</span>'
    : '<span class="chip">not deployed</span>';

  const chips = [summary];
  if (!p.has_env && p.has_env_example)
    chips.push('<span class="chip warn" title="This project has a .env.example but no .env — copy it and fill in the values">.env missing</span>');
  if (p.has_build) chips.push('<span class="chip info">build</span>');
  if (p.status_error) chips.push(`<span class="chip err" title="${esc(p.status_error)}">status error</span>`);

  const rows = p.services.map((s) => {
    const st = p.status[s.name];
    const svc = serviceState(p, s);
    const image = st && st.image ? st.image : (s.image || "");
    const ports = st && st.ports && st.ports.length ? st.ports.join(", ") : s.ports.join(", ");
    return `
      <div class="svc-row">
        <span class="dot ${svc.cls}"></span>
        <span class="svc-name" title="${esc(s.name)}">${esc(s.name)}</span>
        <span class="svc-image" title="${esc(image)}">${esc(image)}</span>
        <span class="svc-state">${svc.label}</span>
        <span class="svc-ports" title="${esc(ports)}">${esc(ports)}</span>
      </div>`;
  }).join("");

  const card = document.createElement("article");
  card.className = "card";
  card.innerHTML = `
    <div class="card-head">
      ${ICONS.cube}
      <span class="card-title" title="${esc(p.name)}">${esc(p.name)}</span>
      <span class="chips">${chips.join("")}</span>
    </div>
    ${p.description ? `<div class="card-desc">${esc(p.description)}</div>` : ""}
    <div class="svc-list">${rows || '<div class="svc-row"><span class="muted small">no services</span></div>'}</div>
    <div class="card-foot">
      <span class="menu-wrap">
        <button class="btn btn-primary" data-menu="deploy" ${busy ? "disabled" : ""}>
          ${ICONS.play} Deploy ${ICONS.caret}
        </button>
        <div class="menu">
          <button data-act="deploy" ${busy ? "disabled" : ""}>Deploy</button>
          <button data-act="deploy-pull" ${busy ? "disabled" : ""}>Pull latest &amp; deploy</button>
          ${p.has_build ? `<div class="sep"></div><button data-act="deploy-build" ${busy ? "disabled" : ""}>Build &amp; deploy</button>` : ""}
        </div>
      </span>
      <span class="menu-wrap">
        <button class="btn btn-danger" data-menu="stop" ${busy || up === 0 ? "disabled" : ""}>
          ${ICONS.stop} Stop ${ICONS.caret}
        </button>
        <div class="menu">
          <button data-act="stop" ${busy || up === 0 ? "disabled" : ""}>Stop</button>
          <div class="sep"></div>
          <button class="danger" data-act="stop-volumes" ${busy || up === 0 ? "disabled" : ""}>Stop &amp; remove volumes</button>
          <div class="hint">Removing volumes deletes stored data</div>
        </div>
      </span>
      <button class="btn" data-act="restart" title="Restart services" ${busy || up === 0 ? "disabled" : ""}>
        ${ICONS.restart} Restart
      </button>
      <button class="btn btn-ghost" data-act="logs" title="View logs">
        ${ICONS.terminal} Logs
      </button>
    </div>`;

  card.addEventListener("click", (ev) => {
    const menuBtn = ev.target.closest("[data-menu]");
    if (menuBtn) {
      const menu = menuBtn.parentElement.querySelector(".menu");
      const wasOpen = menu.classList.contains("open");
      closeMenus();
      if (!wasOpen) menu.classList.add("open");
      ev.stopPropagation();
      return;
    }
    const btn = ev.target.closest("button[data-act]");
    if (!btn) return;
    closeMenus();
    handleAction(p, btn.dataset.act, ev);
  });

  return card;
}

function closeMenus() {
  $$(".menu.open").forEach((m) => m.classList.remove("open"));
}
document.addEventListener("click", closeMenus);

async function handleAction(p, act, ev) {
  const host = state.hosts.find((h) => h.id === state.hostId);
  if (!host) return;
  if (act === "logs") { openLogs(p); return; }
  if (act === "stop-volumes") {
    if (!confirm(`Stop ${p.name} on ${host.name} and REMOVE ITS VOLUMES?\nStored data will be deleted.`)) return;
  }
  const body = { host_id: host.id };
  let path, label;
  switch (act) {
    case "deploy": path = "/deploy"; label = "Deploy"; break;
    case "deploy-pull": path = "/deploy"; body.pull = true; label = "Pull & deploy"; break;
    case "deploy-build": path = "/deploy"; body.build = true; label = "Build & deploy"; break;
    case "stop": path = "/stop"; label = "Stop"; break;
    case "stop-volumes": path = "/stop"; body.volumes = true; label = "Stop + remove volumes"; break;
    case "restart": path = "/restart"; label = "Restart"; break;
    default: return;
  }
  try {
    const { job } = await api(`/projects/${encodeURIComponent(p.name)}${path}`, { method: "POST", body });
    startJobWatcher(job);
  } catch (e) {
    toast(`${label} failed: ${e.message}`, "error");
  }
}

/* ---------- job console ---------- */

function startJobWatcher(job) {
  state.job = job;
  state.jobOffset = 0;
  $("#jobconsole").classList.remove("hidden");
  $("#job-title").textContent = job.description;
  $("#job-output").textContent = "";
  setJobBadge(job);
  pollJob();
  loadOverview(); // refresh states in background
}

function setJobBadge(job) {
  const b = $("#job-badge");
  b.className = "badge " + job.status;
  b.textContent = job.status === "running" ? "running…" : (job.status === "success" ? "done" : "failed");
}

async function pollJob() {
  if (state.jobTimer) clearInterval(state.jobTimer);
  state.jobTimer = setInterval(async () => {
    const job = state.job;
    if (!job) return clearInterval(state.jobTimer);
    let fresh;
    try {
      fresh = await api(`/jobs/${job.id}`);
    } catch (e) {
      return;
    }
    const { job: j } = fresh;
    state.job = j;
    setJobBadge(j);
    const out = $("#job-output");
    const atBottom = out.scrollTop + out.clientHeight >= out.scrollHeight - 30;
    if (j.output.length > state.jobOffset) {
      out.textContent += j.output.slice(state.jobOffset).join("\n") + (atBottom ? "\n" : "");
      state.jobOffset = j.output.length;
    }
    if (atBottom) out.scrollTop = out.scrollHeight;
    if (j.status !== "running") {
      clearInterval(state.jobTimer);
      state.jobTimer = null;
      if (j.status === "success") toast(`${j.description} — done`, "success");
      else toast(`${j.description} — failed (exit ${j.exit_code})`, "error");
      state.job = null;
      loadOverview();
      refreshHostDots();
    }
  }, 1500);
}

$("#job-close").addEventListener("click", () => {
  $("#jobconsole").classList.add("hidden");
  if (state.jobTimer) clearInterval(state.jobTimer);
  state.jobTimer = null;
  state.job = null;
});

/* ---------- logs modal ---------- */

function openLogs(p) {
  const host = state.hosts.find((h) => h.id === state.hostId);
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.innerHTML = `
    <div class="modal logs">
      <div class="modal-head">
        <h2>${esc(p.name)} — logs on ${esc(host.name)}</h2>
        <button class="btn btn-ghost icon-btn" id="logs-close" title="Close">${ICONS.x}</button>
      </div>
      <div class="logs-bar">
        <select id="logs-service">
          <option value="">All services</option>
          ${p.services.map((s) => `<option value="${esc(s.name)}">${esc(s.name)}</option>`).join("")}
        </select>
        <select id="logs-tail">
          <option value="200">200 lines</option>
          <option value="400" selected>400 lines</option>
          <option value="1000">1000 lines</option>
        </select>
        <span class="muted small">refreshes every 3s</span>
        <span class="grow"></span>
      </div>
      <pre class="logs-body" id="logs-body">(loading…)</pre>
    </div>`;
  $("#modal-root").appendChild(overlay);

  const close = () => {
    if (state.logTimer) clearInterval(state.logTimer);
    state.logTimer = null;
    state.logProject = null;
    overlay.remove();
  };
  overlay.addEventListener("click", (ev) => { if (ev.target === overlay) close(); });
  overlay.querySelector("#logs-close").addEventListener("click", close);
  document.addEventListener("keydown", function onEsc(ev) {
    if (ev.key === "Escape") { close(); document.removeEventListener("keydown", onEsc); }
  });

  const refreshLogs = async () => {
    const svc = overlay.querySelector("#logs-service").value;
    const tail = overlay.querySelector("#logs-tail").value;
    try {
      const text = await api(
        `/projects/${encodeURIComponent(p.name)}/logs?host_id=${encodeURIComponent(host.id)}` +
        `&service=${encodeURIComponent(svc)}&tail=${tail}`
      );
      const body = overlay.querySelector("#logs-body");
      const atBottom = body.scrollTop + body.clientHeight >= body.scrollHeight - 40;
      body.textContent = text;
      if (atBottom) body.scrollTop = body.scrollHeight;
    } catch (e) {
      overlay.querySelector("#logs-body").textContent = "error: " + e.message;
    }
  };

  overlay.querySelector("#logs-service").addEventListener("change", refreshLogs);
  overlay.querySelector("#logs-tail").addEventListener("change", refreshLogs);
  refreshLogs();
  state.logTimer = setInterval(refreshLogs, 3000);
  state.logProject = p.name;
}

/* ---------- host modal ---------- */

function openHostModal(host) {
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.innerHTML = `
    <div class="modal">
      <div class="modal-head">
        <h2>${host ? "Edit host" : "Add Docker host"}</h2>
        <button class="btn btn-ghost icon-btn" id="host-close" title="Close">${ICONS.x}</button>
      </div>
      <div class="modal-body">
        <div class="field">
          <label for="h-name">Name</label>
          <input id="h-name" maxlength="32" placeholder="lab" value="${esc(host ? host.name : "")}">
        </div>
        <div class="field">
          <label for="h-address">Address</label>
          <input id="h-address" placeholder="tcp://192.168.70.5:2376" value="${esc(host ? host.address : "")}">
          <div class="hint">unix:///var/run/docker.sock · tcp://host:port · tls://host:port (empty = local socket)</div>
        </div>
        <div class="field">
          <label for="h-desc">Description</label>
          <input id="h-desc" maxlength="200" placeholder="optional" value="${esc(host ? host.description : "")}">
        </div>
        <div class="test-row">
          <button class="btn" id="h-test">Test connection</button>
          <span class="test-result" id="h-test-result"></span>
        </div>
      </div>
      <div class="modal-foot">
        <button class="btn btn-ghost" id="h-cancel">Cancel</button>
        <button class="btn btn-primary" id="h-save">${host ? "Save" : "Add host"}</button>
      </div>
    </div>`;
  $("#modal-root").appendChild(overlay);

  const close = () => overlay.remove();
  const readForm = () => ({
    name: overlay.querySelector("#h-name").value,
    address: overlay.querySelector("#h-address").value,
    description: overlay.querySelector("#h-desc").value,
  });

  overlay.addEventListener("click", (ev) => { if (ev.target === overlay) close(); });
  overlay.querySelector("#host-close").addEventListener("click", close);
  overlay.querySelector("#h-cancel").addEventListener("click", close);
  document.addEventListener("keydown", function onEsc(ev) {
    if (ev.key === "Escape") { close(); document.removeEventListener("keydown", onEsc); }
  });

  overlay.querySelector("#h-test").addEventListener("click", async (ev) => {
    const btn = ev.currentTarget;
    const result = overlay.querySelector("#h-test-result");
    btn.disabled = true;
    result.className = "test-result";
    result.innerHTML = '<span class="spin"></span> &nbsp;testing…';
    try {
      const info = await api("/hosts/test", { method: "POST", body: { address: readForm().address } });
      if (info.ok) {
        result.className = "test-result ok";
        result.textContent = `✓ docker ${info.version} · ${info.containers_running ?? 0}/${info.containers ?? 0} containers`;
      } else {
        result.className = "test-result err";
        result.textContent = "✗ " + (info.error || "unreachable");
      }
    } catch (e) {
      result.className = "test-result err";
      result.textContent = "✗ " + e.message;
    }
    btn.disabled = false;
  });

  overlay.querySelector("#h-save").addEventListener("click", async () => {
    const body = readForm();
    try {
      if (host) {
        const { host: updated } = await api(`/hosts/${encodeURIComponent(host.id)}`, { method: "PUT", body });
        state.hosts = state.hosts.map((h) => (h.id === host.id ? updated : h));
        delete state.hostInfo[host.id];
        toast(`Host ${updated.name} updated`, "success");
      } else {
        const { host: created } = await api("/hosts", { method: "POST", body });
        state.hosts.push(created);
        toast(`Host ${created.name} added`, "success");
      }
      close();
      renderHosts();
      if (state.hostId) await loadOverview();
      refreshHostDots();
    } catch (e) {
      toast(e.message, "error");
    }
  });

  setTimeout(() => overlay.querySelector("#h-name").focus(), 50);
}

function confirmRemoveHost(h) {
  if (state.hosts.length <= 1) { toast("Cannot remove the last host", "error"); return; }
  if (!confirm(`Remove host "${h.name}" (${h.address})?`)) return;
  api(`/hosts/${encodeURIComponent(h.id)}`, { method: "DELETE" })
    .then(() => {
      state.hosts = state.hosts.filter((x) => x.id !== h.id);
      if (state.hostId === h.id) {
        state.hostId = state.hosts[0].id;
        localStorage.setItem("deployer.hostId", state.hostId);
        return loadOverview();
      }
      renderHosts();
      toast(`Host ${h.name} removed`, "success");
    })
    .catch((e) => toast(e.message, "error"));
}

/* ---------- auto refresh ---------- */

function startAutoRefresh() {
  setInterval(() => {
    if (!state.autoRefresh || document.hidden) return;
    if (state.job && state.job.status === "running") return;
    loadOverview();
    if (Math.random() < 0.2) refreshHostDots(); // host pings are slow; do them occasionally
  }, 10000);
}

/* ---------- events ---------- */

$("#refresh").addEventListener("click", () => { loadOverview(); refreshHostDots(); });
$("#add-host").addEventListener("click", () => openHostModal(null));
$("#autorefresh").addEventListener("change", (ev) => { state.autoRefresh = ev.target.checked; });
$("#logout").addEventListener("click", () => {
  state.token = "";
  localStorage.removeItem("deployer.token");
  showLogin();
});

$("#login-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  state.token = $("#login-token").value.trim();
  if (!state.token) return;
  localStorage.setItem("deployer.token", state.token);
  $("#login-error").classList.add("hidden");
  $("#login").classList.add("hidden");
  init().catch((e) => {
    $("#login-error").textContent = e.message === "unauthorized" ? "Wrong token" : e.message;
    $("#login-error").classList.remove("hidden");
    $("#login").classList.remove("hidden");
    state.token = "";
    localStorage.removeItem("deployer.token");
  });
});

init().catch((e) => console.error(e));
