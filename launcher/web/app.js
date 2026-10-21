let state = { cfg: null, versions: [], filter: "all", selected: null, logOffset: 0, logPath: null };

const $ = (id) => document.getElementById(id);

async function api(path, opts) {
  const r = await fetch(path, opts);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || r.status);
  return j;
}

function kind(id) {
  if (id.startsWith("fabric")) return "fabric";
  if (id.startsWith("neoforge")) return "neoforge";
  if (id.includes("forge")) return "forge";
  return "vanilla";
}

function renderVersions() {
  const list = $("verlist");
  const items = state.versions.filter(v => state.filter === "all" || kind(v.id) === state.filter);
  list.innerHTML = "";
  for (const v of items) {
    const el = document.createElement("div");
    el.className = "ver" + (state.selected === v.id ? " sel" : "");
    el.innerHTML = `<div class="id">${v.id}</div>
      <div class="meta">${kind(v.id)}${v.inherits ? " · 基于 " + v.inherits : ""}</div>`;
    el.onclick = () => select(v.id);
    el.ondblclick = () => play(v.id);
    list.appendChild(el);
  }
  if (!items.length) list.innerHTML = `<div class="ver"><div class="meta">还没有安装版本，先在上方“下载 / 安装”</div></div>`;
}

function select(id) {
  state.selected = id;
  $("selinfo").textContent = "已选择：" + id;
  $("play").disabled = false;
  renderVersions();
}

async function refresh() {
  try {
    const cfg = await api("/api/config");
    state.cfg = cfg;
    $("username").value = cfg.username || "Player";
    $("mem").value = cfg.mem || "2G";
    $("root").value = cfg.root || "";
    const st = await api("/api/status");
    state.versions = st.versions || [];
    $("dot").classList.add("ok");
    $("statusText").textContent = "Java: " + st.java;
    renderVersions();
  } catch (e) {
    $("dot").classList.remove("ok");
    $("statusText").textContent = "连接失败: " + e.message;
  }
}

async function loadManifest() {
  try {
    const data = await api("/api/versions");
    state.manifest = data.versions || [];
    renderManifest();
  } catch (e) {
    console.warn("manifest", e);
  }
}

function renderManifest() {
  const dl = $("mcvers");
  dl.innerHTML = "";
  const all = $("allsnap") && $("allsnap").checked;
  for (const v of (state.manifest || [])) {
    if (!all && v.type !== "release") continue;
    const o = document.createElement("option");
    o.value = v.id;
    o.label = v.type;
    dl.appendChild(o);
  }
}

async function install() {
  const mc = $("mcver").value.trim();
  if (!mc) return alert("先填版本号，例如 1.21.1");
  try {
    await api("/api/install", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mc, loader: $("loader").value }) });
  } catch (e) {
    alert("安装失败: " + e.message);
  }
}

function pollTask() {
  api("/api/task").then(t => {
    const pct = t.total ? Math.round(100 * t.done / t.total) : (t.phase === "done" ? 100 : 0);
    $("bar").style.width = pct + "%";
    $("taskmsg").textContent = t.error ? "错误: " + t.error
      : `${t.phase} · ${t.message} ${t.total ? `(${t.done}/${t.total})` : ""}`;
    if (t.phase === "done") { setTimeout(refresh, 500); }
  }).catch(() => {});
}

async function play(versionId) {
  const vid = versionId || state.selected;
  if (!vid) return;
  try {
    const r = await api("/api/launch", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version_id: vid, username: $("username").value.trim() || "Player" }) });
    state.logPath = r.log;
    state.logOffset = 0;
    $("console").textContent = "启动中 pid=" + r.pid + "\n";
    pollLog();
  } catch (e) {
    $("console").textContent = "启动失败: " + e.message;
  }
}

function pollLog() {
  if (!state.logPath) return;
  api(`/log/${encodeURI(state.logPath)}?offset=${state.logOffset}`).then(r => {
    state.logOffset = r.offset;
    if (r.text) {
      const box = $("console");
      const atBottom = box.scrollTop + box.clientHeight >= box.scrollHeight - 20;
      box.textContent += r.text;
      if (atBottom) box.scrollTop = box.scrollHeight;
    }
    setTimeout(pollLog, 1000);
  }).catch(() => setTimeout(pollLog, 2000));
}

async function saveCfg() {
  await api("/api/config", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ root: $("root").value.trim(), username: $("username").value.trim(),
      mem: $("mem").value.trim() || "2G" }) });
  refresh();
}

$("tabs").onclick = (e) => {
  if (e.target.tagName !== "BUTTON") return;
  for (const b of $("tabs").children) b.classList.remove("on");
  e.target.classList.add("on");
  state.filter = e.target.dataset.filter;
  renderVersions();
};
$("refresh").onclick = refresh;
$("save").onclick = saveCfg;
$("install").onclick = install;
$("play").onclick = () => play();
$("allsnap").onchange = renderManifest;
$("openRoot").onclick = async () => {
  const cfg = await api("/api/config");
  window.open("file:///" + cfg.root.replace(/\\/g, "/"));
};

refresh();
loadManifest();
setInterval(pollTask, 1200);
setInterval(refresh, 5000);
