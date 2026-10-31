// Real interaction pass over the launcher page: select a version, switch list
// modes, search, open advanced settings - and collect any page errors.
const CDP = "http://127.0.0.1:9222";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function getWsUrl() {
  const targets = await (await fetch(CDP + "/json")).json();
  const page = targets.find((t) => t.type === "page" && t.url.startsWith("http://127.0.0.1:8765"));
  if (page) return page.webSocketDebuggerUrl;
  const fresh = await (await fetch(CDP + "/json/new?http://127.0.0.1:8765/", { method: "PUT" })).json();
  return fresh.webSocketDebuggerUrl;
}

const ws = new WebSocket(await getWsUrl());
let seq = 0;
const pending = new Map();
const errors = [];
ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg);
    pending.delete(msg.id);
  } else if (msg.method === "Runtime.exceptionThrown") {
    errors.push(msg.params.exceptionDetails.text + " " +
      (msg.params.exceptionDetails.exception?.description || ""));
  } else if (msg.method === "Runtime.consoleAPICalled" && msg.params.type === "error") {
    errors.push(msg.params.args.map((a) => a.value ?? a.description).join(" "));
  }
};
const send = (method, params = {}) => new Promise((resolve) => {
  const id = ++seq;
  pending.set(id, resolve);
  ws.send(JSON.stringify({ id, method, params }));
});
await new Promise((r) => (ws.onopen = r));
await send("Runtime.enable");
await send("Page.enable");
await send("Network.enable");
await send("Network.setCacheDisabled", { cacheDisabled: true });
await send("Page.navigate", { url: "http://127.0.0.1:8765/?v=ui216" });
await sleep(500);

const evalJs = async (expression) => {
  const r = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  if (r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails));
  return r.result.result.value;
};

for (let i = 0; i < 60; i++) {
  if (await evalJs("document.getElementById('mcver') && document.getElementById('mcver').options.length > 0")) break;
  await sleep(500);
}

const result = await evalJs(`(async () => {
  const out = {};
  const $ = (id) => document.getElementById(id);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // 1. select a version row -> selinfo + play button state
  const row = document.querySelector("#verlist .ver");
  row.click();
  out.afterSelect = { selinfo: $("selinfo").textContent, playDisabled: $("play").disabled,
    mcver: $("mcver").value, rowMarked: !!document.querySelector("#verlist .ver.sel") };

  // 2. keyboard select (Enter) on the next row
  const rows = document.querySelectorAll("#verlist .ver");
  rows[1].dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }));
  out.keyboardSelect = $("selinfo").textContent;

  // 3. mode switch
  $("modeInstalled").click();
  out.installedMode = { empty: document.querySelector("#verlist .ver.empty") !== null,
    pressed: $("modeInstalled").getAttribute("aria-pressed") };
  $("modeInstall").click();

  // 4. search filter
  $("verSearch").value = "1.21.1";
  $("verSearch").dispatchEvent(new Event("input", { bubbles: true }));
  out.searchRows = document.querySelectorAll("#verlist .ver").length;
  out.searchFirst = document.querySelector("#verlist .ver .id")?.textContent || "";
  $("verSearch").value = "";
  $("verSearch").dispatchEvent(new Event("input", { bubbles: true }));

  // 5. loader switch triggers loader-version query
  $("loader").value = "fabric";
  $("loader").dispatchEvent(new Event("change", { bubbles: true }));
  await sleep(2500);
  out.loaderVerOptions = $("loaderVer").options.length;
  out.loaderVerFirst = $("loaderVer").options[0]?.textContent || "";

  // 6. vanilla disables loader version
  $("loader").value = "vanilla";
  $("loader").dispatchEvent(new Event("change", { bubbles: true }));
  await sleep(300);
  out.vanillaLoaderVer = { disabled: $("loaderVer").disabled, text: $("loaderVer").options[0]?.textContent || "" };
  $("loader").value = "fabric";
  $("loader").dispatchEvent(new Event("change", { bubbles: true }));

  // 7. advanced section opens and jvm/mod/mrpack selects got populated
  document.querySelector(".adv summary").click();
  await sleep(500);
  out.adv = { open: document.querySelector(".adv").open,
    jvm: $("jvmSelect").options.length, mods: $("modPick").options.length,
    mrpacks: $("mrpackPick").options.length };

  // 8. pick-release shortcut
  $("pickRelease").click();
  out.picked = $("mcver").value;
  return out;
})()`);

// layout overflow probe at a narrow width
await send("Emulation.setDeviceMetricsOverride", { width: 900, height: 700, deviceScaleFactor: 1, mobile: false });
await sleep(400);
const narrow = await evalJs("({overflow: document.documentElement.scrollWidth > window.innerWidth + 1, sw: document.documentElement.scrollWidth})");
await send("Emulation.setDeviceMetricsOverride", { width: 480, height: 800, deviceScaleFactor: 1, mobile: true });
await sleep(400);
const mobile = await evalJs("({overflow: document.documentElement.scrollWidth > window.innerWidth + 1, sw: document.documentElement.scrollWidth})");
await send("Emulation.clearDeviceMetricsOverride");

console.log(JSON.stringify({ result, narrow, mobile, errors }, null, 2));
ws.close();
process.exit(errors.length ? 1 : 0);
