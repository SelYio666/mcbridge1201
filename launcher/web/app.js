let state = { cfg: null, versions: [], mode: "installable", query: "", selected: null, logOffset: 0, logPath: null, manifest: [], latest: {} };
let oneClickTimer = null;
let loaderRequest = 0;

const $ = (id) => document.getElementById(id);

function setTaskMessage(text, kind = "") {
  const box = $("taskmsg");
  box.textContent = text;
  box.classList.toggle("error", kind === "error");
  box.classList.toggle("busy", kind === "busy");
}

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

function installedIds() {
  return new Set((state.versions || []).map(v => v.id));
}

function renderVersions() {
  const list = $("verlist");
  const inst = installedIds();
  list.innerHTML = "";
  const q = state.query.trim().toLowerCase();

  let items;
  if (state.mode === "installed") {
    items = (state.versions || []).filter(v => !q || v.id.toLowerCase().includes(q));
  } else {
    const all = $("allsnap") && $("allsnap").checked;
    items = (state.manifest || [])
      .filter(v => all || v.type === "release")
      .filter(v => !q || v.id.toLowerCase().includes(q))
      .map(v => ({ id: v.id, type: v.type, inherits: null }));
  }

  if ($("cntInstall")) $("cntInstall").textContent = `(${(state.manifest || []).length})`;
  if ($("cntInstalled")) $("cntInstalled").textContent = `(${(state.versions || []).length})`;

  const MAX_RENDERED = 2000;
  const shown = items.slice(0, MAX_RENDERED);
  if ($("vercount")) {
    const total = state.mode === "installed" ? (state.versions || []).length
      : (state.manifest || []).length;
    const more = items.length > MAX_RENDERED ? "，其余请用搜索或下拉选择" : "";
    $("vercount").textContent = state.mode === "installed"
      ? `已安装 ${total} 个（当前列出 ${shown.length} 个${more}）`
      : `共 ${total} 个版本可选（当前列出 ${shown.length} 个${more}）`;
  }

  for (const v of shown) {
    const el = document.createElement("div");
    el.className = "ver" + (state.selected === v.id ? " sel" : "");
    el.setAttribute("role", "option");
    el.setAttribute("tabindex", "0");
    el.setAttribute("aria-selected", state.selected === v.id ? "true" : "false");
    const type = v.inherits ? kind(v.id) : (v.type === "release" ? "正式版" : (TYPE_LABEL[v.type] || v.type));
    el.innerHTML = `<div class="id">${v.id}${inst.has(v.id) ? ' <span class="badge">已安装</span>' : ""}</div>
      <div class="meta">${type}${v.inherits ? " · 基于 " + v.inherits : ""}
        ${inst.has(v.id) ? '<a class="del" data-id="' + v.id + '">删除</a> <a class="del" data-dir="' + v.id + '">目录</a>' : ""}</div>`;
    el.onclick = (e) => {
      if (e.target.classList && e.target.classList.contains("del")) {
        e.stopPropagation();
        if (e.target.dataset.dir) {
          openDir("version", e.target.dataset.dir);
        } else {
          deleteVersion(e.target.dataset.id);
        }
        return;
      }
      state.selected = v.id;
      if ($("mcver")) $("mcver").value = v.id;
      $("selinfo").textContent = "已选择：" + v.id;
      $("play").disabled = !inst.has(v.id);
      renderVersions();
    };
    el.onkeydown = (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        el.click();
      }
    };
    el.ondblclick = () => {
      if ($("mcver")) $("mcver").value = v.id;
      oneClick();
    };
    list.appendChild(el);
  }
  if (!items.length) {
    list.innerHTML = `<div class="ver empty"><strong>没有找到版本</strong><div class="meta">试试其他关键词，或切换版本分类</div></div>`;
  } else if (items.length > 400) {
    const more = document.createElement("div");
    more.className = "ver more";
    more.innerHTML = `<div class="meta">还有 ${items.length - 400} 个版本<br>输入关键词可缩小范围</div>`;
    list.appendChild(more);
  }
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
    if (!$("username").value) $("username").value = cfg.username || "Player";
    if (!$("mem").value) $("mem").value = cfg.mem || "2G";
    if (!$("root").value) $("root").value = cfg.root || "";
    if ($("downloadSource")) $("downloadSource").value = cfg.download_source || "auto";
    const st = await api("/api/status");
    state.versions = st.versions || [];
    $("dot").classList.add("ok");
    document.querySelector(".statusline").classList.remove("error");
    $("statusText").textContent = st.java ? "Java 已就绪 · " + st.java : "未找到 Java · 请先安装运行时";
    $("statusText").title = st.java || st.java_error || "未找到 Java";
    renderVersions();
    loadSourceStatus();
  } catch (e) {
    $("dot").classList.remove("ok");
    document.querySelector(".statusline").classList.add("error");
    $("statusText").textContent = "本地服务连接失败 · " + e.message;
    $("statusText").title = e.message;
  }
}

async function loadManifest() {
  try {
    const data = await api("/api/versions");
    state.manifest = data.versions || [];
    state.latest = data.latest || {};
    renderManifest(true);
    loadLoaderVersions();
  } catch (e) {
    console.warn("manifest", e);
  }
}

const TYPE_LABEL = { release: "正式版", snapshot: "快照", old_beta: "远古 Beta", old_alpha: "远古 Alpha" };

function renderManifest(initial) {
  const sel = $("mcver");
  if (!sel) return;
  const prev = sel.value;
  const all = $("allsnap") && $("allsnap").checked;
  sel.innerHTML = "";

  const addGroup = (label, items) => {
    if (!items.length) return;
    const g = document.createElement("optgroup");
    g.label = label;
    for (const v of items) {
      const o = document.createElement("option");
      o.value = v.id;
      o.textContent = v.id + (v.type === "release" ? "" : `（${TYPE_LABEL[v.type] || v.type}）`);
      g.appendChild(o);
    }
    sel.appendChild(g);
  };

  const versions = state.manifest || [];
  const latest = state.latest || {};
  const releaseList = versions.filter(v => v.type === "release");
  const snapshotList = versions.filter(v => v.type === "snapshot");
  const oldList = versions.filter(v => v.type !== "release" && v.type !== "snapshot");

  addGroup("正式版", releaseList);
  if (all) addGroup("快照", snapshotList);
  if (all) addGroup("远古版本", oldList);

  const fallback = latest.release || (releaseList[0] && releaseList[0].id) || "";
  sel.value = initial || !prev ? fallback : prev;
  if (!sel.value) sel.value = fallback;
  // The count label is owned by renderVersions(): the select's option count includes
  // versions the list intentionally filters out (snapshots/old), so it was misleading.
}

async function deleteVersion(id) {
  if (!confirm("删除版本 " + id + "？只删 versions/ 下的这个版本，不动存档和模组。")) return;
  try {
    const r = await api("/api/delete-version", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id })
    });
    $("taskmsg").textContent = "已删除 " + r.deleted + "，释放 " + Math.round(r.freed_bytes / 1048576) + " MB";
    refresh();
  } catch (e) {
    alert("删除失败: " + e.message);
  }
}

function setButton(busy, text) {
  const b = $("install");
  b.disabled = busy;
  b.textContent = text;
}

async function oneClick() {
  const mc = $("mcver").value.trim();
  if (!mc) return alert("先填版本号，例如 1.21.1");
  setButton(true, "安装中…");
  $("console").textContent = "开始安装 " + mc + " …\n";
  try {
    await api("/api/install", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mc, loader: $("loader").value,
        loader_version: $("loaderVer") && $("loaderVer").value ? $("loaderVer").value : null })
    });
  } catch (e) {
    alert("安装失败: " + e.message);
    setButton(false, "安装并启动");
    return;
  }
  clearInterval(oneClickTimer);
  oneClickTimer = setInterval(async () => {
    let t;
    try { t = await api("/api/task"); } catch { return; }
    if (t.phase === "error") {
      clearInterval(oneClickTimer);
      setButton(false, "安装并启动");
      $("taskmsg").textContent = "错误: " + t.error;
      alert("安装失败: " + t.error);
      return;
    }
    if (t.phase === "done") {
      clearInterval(oneClickTimer);
      setButton(false, "安装并启动");
      await refresh();
      const vid = t.message && t.message.includes("loader") || t.message && t.message.includes("forge") || t.message && t.message.includes("neoforge")
        ? t.message : mc;
      await play(vid);
    }
  }, 1500);
}

function fmtBytes(n) {
  if (!n) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = n;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value >= 100 ? value.toFixed(0) : value.toFixed(1)} ${units[unit]}`;
}

function hostOf(url) {
  try { return new URL(url).host; } catch { return url || ""; }
}

function pollTask() {
  api("/api/task").then(t => {
    const pct = t.total ? Math.round(100 * t.done / t.total) : (t.phase === "done" ? 100 : 0);
    $("bar").style.width = pct + "%";
    const files = t.total ? `(${t.done}/${t.total})` : "";
    const transfer = [t.bytes_done ? fmtBytes(t.bytes_done) : "",
                      t.speed ? `${fmtBytes(t.speed)}/s` : ""].filter(Boolean).join(" · ");
    const source = t.source ? ` ← ${hostOf(t.source)}` : "";
    $("taskmsg").textContent = t.error ? "错误: " + t.error
      : `${t.phase} · ${t.message} ${files}${transfer ? " · " + transfer : ""}${source}`;
    $("taskmsg").title = t.source || "";
  }).catch(() => {});
}

async function play(versionId) {
  const vid = versionId || state.selected;
  if (!vid) return;
  try {
    const r = await api("/api/launch", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version_id: vid, username: $("username").value.trim() || "Player" })
    });
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
  api(`/log/${encodeURIComponent(state.logPath)}?offset=${state.logOffset}`).then(r => {
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
  await api("/api/config", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      root: $("root").value.trim() || state.cfg.root,
      username: $("username").value.trim() || "Player",
      mem: $("mem").value.trim() || "2G",
      download_source: $("downloadSource") ? $("downloadSource").value : "auto"
    })
  });
  refresh();
}

$("modeInstall").onclick = () => {
  state.mode = "installable";
  $("modeInstall").classList.add("on");
  $("modeInstall").setAttribute("aria-pressed", "true");
  $("modeInstalled").classList.remove("on");
  $("modeInstalled").setAttribute("aria-pressed", "false");
  renderVersions();
};
$("modeInstalled").onclick = () => {
  state.mode = "installed";
  $("modeInstalled").classList.add("on");
  $("modeInstalled").setAttribute("aria-pressed", "true");
  $("modeInstall").classList.remove("on");
  $("modeInstall").setAttribute("aria-pressed", "false");
  renderVersions();
};
$("verSearch").oninput = (e) => { state.query = e.target.value; renderVersions(); };
$("refresh").onclick = refresh;
$("save").onclick = saveCfg;
$("install").onclick = oneClick;
$("play").onclick = () => play();
$("allsnap").onchange = () => { renderManifest(false); renderVersions(); };
$("loader").onchange = loadLoaderVersions;
$("jvmInstall").onclick = installJvm;
$("modToggle").onclick = toggleMod;
$("modRefresh").onclick = loadMods;
$("mrpackInstall").onclick = installMrpack;
$("mrpackPick").onchange = () => { if ($("mrpackPick").value) $("mrpackPath").value = $("mrpackPick").value; };
$("mcver").onchange = loadLoaderVersions;
$("pickRelease").onclick = () => { if (state.latest.release) { $("mcver").value = state.latest.release; } };
$("pickSnapshot").onclick = () => {
  if (!state.latest.snapshot) return;
  $("allsnap").checked = true;
  renderManifest(false);
  $("mcver").value = state.latest.snapshot;
};
const SOURCE_MODE_LABEL = { auto: "自动（官方优先）", official: "仅官方", mirror: "镜像优先" };

function canarySummary(res) {
  if (!res || !res.result) return "";
  const r = res.result;
  const bits = [`核心${r.core_ok ? "✓" : "✗"}`,
                `镜像${r.mirrors_ok ? "✓" : "✗"}`,
                `NeoForge${r.neoforge_ok ? "✓" : "✗"}`];
  if (r.core_failures && r.core_failures.length) bits.push("核心失败: " + r.core_failures.join(","));
  return bits.join(" · ");
}

async function loadSourceStatus() {
  try {
    const s = await api("/api/source-health");
    const sick = (s.health || []).filter(h => (h.fails || 0) >= 2).length;
    const check = s.check && s.check.running ? "检查中…" : canarySummary(s.check);
    $("sourceStatus").textContent =
      `${SOURCE_MODE_LABEL[s.mode] || s.mode} · 近期异常源 ${sick}${check ? " · " + check : ""}`;
  } catch { /* status text is best effort */ }
}

function pollSourceCheck() {
  api("/api/check-sources").then(s => {
    if (s.running) {
      $("sourceStatus").textContent = "检查中…（约 30 秒）";
      setTimeout(pollSourceCheck, 1500);
    } else if (s.error) {
      $("sourceStatus").textContent = "检查失败: " + s.error;
    } else {
      loadSourceStatus();
    }
  }).catch(() => setTimeout(pollSourceCheck, 2500));
}

async function checkSources() {
  try {
    await api("/api/check-sources", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: "{}"
    });
    $("sourceStatus").textContent = "检查中…（约 30 秒）";
    pollSourceCheck();
  } catch (e) {
    alert("检查下载源失败: " + e.message);
  }
}

async function openDir(target, version) {
  try {
    const r = await api("/api/open-dir", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target, version: version || "" })
    });
    $("taskmsg").textContent = "已打开 " + r.opened;
  } catch (e) {
    alert("打开目录失败: " + e.message);
  }
}

async function syncProfiles() {
  try {
    const r = await api("/api/sync-profiles", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: "{}"
    });
    $("taskmsg").textContent = r.count
      ? `已写入 ${r.count} 个 launcher_profiles 条目：${r.added.join(", ")}`
      : "所有已安装版本都已有 profile 条目";
  } catch (e) {
    alert("写入 profile 失败: " + e.message);
  }
}

async function loadLoaderVersions() {
  const sel = $("loaderVer");
  if (!sel) return;
  const loader = $("loader").value;
  const mc = $("mcver").value.trim();
  const req = ++loaderRequest;
  if (loader === "vanilla") {
    sel.innerHTML = '<option value="">原版无需加载器</option>';
    sel.disabled = true;
    return;
  }
  sel.disabled = false;
  if (!mc) {
    sel.innerHTML = '<option value="">加载器：最新</option>';
    return;
  }
  sel.innerHTML = '<option value="">查询版本中…</option>';
  try {
    const r = await api(`/api/loader-versions?loader=${encodeURIComponent(loader)}&mc=${encodeURIComponent(mc)}`);
    if (req !== loaderRequest) return;
    sel.innerHTML = '<option value="">加载器：最新</option>';
    for (const v of r.versions || []) {
      const o = document.createElement("option");
      o.value = v;
      o.textContent = v;
      sel.appendChild(o);
    }
    sel.title = r.error ? "在线查询失败，安装时将使用最新版" : "";
  } catch (e) {
    if (req !== loaderRequest) return;
    sel.innerHTML = '<option value="">加载器：最新</option>';
    sel.title = "查询失败: " + e.message;
  }
}

async function loadJvm() {
  const sel = $("jvmSelect");
  if (!sel) return;
  try {
    const r = await api("/api/jvm");
    const prev = sel.value;
    const available = r.available || [];
    const installed = r.installed || [];
    sel.innerHTML = "";
    for (const id of available) {
      const o = document.createElement("option");
      o.value = id;
      o.textContent = id + (installed.includes(id) ? "（已安装）" : "");
      sel.appendChild(o);
    }
    if (!available.length) {
      const o = document.createElement("option");
      o.value = "";
      o.textContent = r.error ? "在线查询失败" : "暂无可用运行时";
      sel.appendChild(o);
    }
    if (prev && available.includes(prev)) sel.value = prev;
    $("jvmStatus").textContent = installed.length
      ? "游戏目录已有 " + installed.length + " 个运行时"
      : "游戏目录内暂无专用运行时，启动时用系统 Java";
  } catch (e) {
    $("jvmStatus").textContent = "运行时查询失败: " + e.message;
  }
}

async function loadMods() {
  const sel = $("modPick");
  if (!sel) return;
  try {
    const r = await api("/api/mods");
    const prev = sel.value;
    sel.innerHTML = "";
    for (const m of r.mods || []) {
      const o = document.createElement("option");
      o.value = m.name;
      o.textContent = (m.enabled ? "" : "⏸ ") + m.name;
      sel.appendChild(o);
    }
    if (!(r.mods || []).length) {
      const o = document.createElement("option");
      o.value = "";
      o.textContent = "mods 目录为空";
      sel.appendChild(o);
    }
    if (prev && [...sel.options].some(o => o.value === prev)) sel.value = prev;
  } catch (e) {
    $("taskmsg").textContent = "读取模组失败: " + e.message;
  }
}

async function toggleMod() {
  const name = $("modPick").value;
  if (!name) return alert("先选一个模组");
  try {
    const r = await api("/api/toggle-mod", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name })
    });
    $("taskmsg").textContent = (r.enabled ? "已启用 " : "已禁用 ") + r.name;
    await loadMods();
    $("modPick").value = r.name;
  } catch (e) {
    alert("切换模组失败: " + e.message);
  }
}

async function loadMrpacks() {
  const sel = $("mrpackPick");
  if (!sel) return;
  try {
    const r = await api("/api/mrpacks");
    sel.innerHTML = "";
    const o0 = document.createElement("option");
    o0.value = "";
    o0.textContent = (r.packs || []).length ? "选择整合包…" : "packs / 下载目录中没有 .mrpack";
    sel.appendChild(o0);
    for (const p of r.packs || []) {
      const o = document.createElement("option");
      o.value = p.path;
      const bits = [p.name, p.version, p.minecraft ? "MC " + p.minecraft : ""].filter(Boolean);
      o.textContent = bits.join(" · ") + (p.error ? "（索引不可读）" : "");
      sel.appendChild(o);
    }
  } catch { /* 列表加载失败不阻塞主流程 */ }
}

function watchTask(label, onDone) {
  const timer = setInterval(async () => {
    let t;
    try { t = await api("/api/task"); } catch { return; }
    if (t.phase === "error") {
      clearInterval(timer);
      $("taskmsg").textContent = label + "失败: " + t.error;
      $("taskmsg").classList.add("error");
    } else if (t.phase === "done") {
      clearInterval(timer);
      $("taskmsg").classList.remove("error");
      $("taskmsg").textContent = label + "完成 · " + (t.message || "");
      if (onDone) onDone(t);
    }
  }, 1200);
}

async function installJvm() {
  const id = $("jvmSelect").value;
  if (!id) return alert("先选一个要安装的 Java 运行时");
  try {
    await api("/api/install-jvm", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id })
    });
    $("taskmsg").textContent = "正在安装 Java 运行时 " + id + " …";
    watchTask("Java 运行时", () => loadJvm());
  } catch (e) {
    alert("安装 Java 失败: " + e.message);
  }
}

async function installMrpack() {
  const path = $("mrpackPath").value.trim();
  if (!path) return alert("先选择整合包或粘贴 .mrpack 路径");
  try {
    await api("/api/install-mrpack", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path })
    });
    $("taskmsg").textContent = "正在安装整合包…";
    watchTask("整合包", (t) => {
      refresh();
      if (t.message && t.message.includes("|")) select(t.message.split("|")[1]);
    });
  } catch (e) {
    alert("安装整合包失败: " + e.message);
  }
}

$("openRoot").onclick = () => openDir("root");
$("checkSources").onclick = checkSources;
$("help").onclick = () => window.open("/guide", "_blank");
$("openMods").onclick = () => openDir("mods");
$("openSaves").onclick = () => openDir("saves");
$("modOpen").onclick = () => openDir("mods");
$("syncProfiles").onclick = syncProfiles;

refresh();
loadManifest();
loadJvm();
loadMrpacks();
loadMods();
setInterval(loadJvm, 15000);
setInterval(pollTask, 1200);
setInterval(refresh, 5000);
