// Capture a real page through the browser DevTools protocol (no npm packages).
import { writeFile } from 'node:fs/promises';

const [url, output, widthArg = '1440', heightArg = '960', readyExpression = 'document.readyState === "complete"'] = process.argv.slice(2);
if (!url || !output) throw new Error('usage: node capture_web.mjs <url> <output> [width] [height] [readyExpression]');

const targets = await (await fetch('http://127.0.0.1:9222/json')).json();
const target = targets.find((item) => item.type === 'page');
if (!target) throw new Error('no browser page target');
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  ws.addEventListener('open', resolve, { once: true });
  ws.addEventListener('error', reject, { once: true });
});

let nextId = 1;
const pending = new Map();
const errors = [];
ws.addEventListener('message', (event) => {
  const message = JSON.parse(event.data);
  if (message.id) {
    const handler = pending.get(message.id);
    if (!handler) return;
    pending.delete(message.id);
    if (message.error) handler.reject(new Error(JSON.stringify(message.error)));
    else handler.resolve(message.result);
  } else if (message.method === 'Runtime.exceptionThrown') {
    errors.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
  }
});

function send(method, params = {}) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
  return result.result.value;
}

await send('Page.enable');
await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', {
  width: Number(widthArg), height: Number(heightArg), deviceScaleFactor: 1, mobile: false,
});
await send('Page.navigate', { url });
const deadline = Date.now() + 30000;
let ready = false;
while (Date.now() < deadline) {
  try {
    ready = Boolean(await evaluate(readyExpression));
  } catch {
    ready = false;
  }
  if (ready) break;
  await new Promise((resolve) => setTimeout(resolve, 200));
}
await new Promise((resolve) => setTimeout(resolve, 600));
const screenshot = await send('Page.captureScreenshot', { format: 'png', fromSurface: true });
await writeFile(output, Buffer.from(screenshot.data, 'base64'));
const info = await evaluate(`({
  title: document.title,
  width: innerWidth,
  height: innerHeight,
  scrollWidth: document.documentElement.scrollWidth,
  scrollHeight: document.documentElement.scrollHeight,
  status: document.getElementById('statusText')?.textContent || null,
  versions: document.querySelectorAll('#verlist .ver').length,
  text: document.body.innerText.slice(0, 500)
})`);
console.log(JSON.stringify({ output, ready, errors, ...info }, null, 2));
ws.close();
if (!ready || errors.length) process.exitCode = 1;
