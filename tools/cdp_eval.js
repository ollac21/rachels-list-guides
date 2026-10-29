#!/usr/bin/env node
// Open a built page in headless Chrome (phone width), run a JS file in it, print the JSON it returns.
//   node tools/cdp_eval.js <url> <script.js> [--w 390]
const { spawn } = require("child_process");
const fs = require("fs"), os = require("os"), path = require("path");
const args = process.argv.slice(2);
const url = args[0], code = fs.readFileSync(args[1], "utf8");
const W = +(args.includes("--w") ? args[args.indexOf("--w") + 1] : 390);
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const port = 9300 + Math.floor(Math.random() * 500), profile = fs.mkdtempSync(path.join(os.tmpdir(), "cdp-"));
  const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-first-run", "--mute-audio", "--remote-debugging-port=" + port, "--user-data-dir=" + profile, "about:blank"], { stdio: "ignore" });
  try {
    let ver; for (let i = 0; i < 60; i++) { try { ver = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); break; } catch (e) { await sleep(250); } }
    const ws = new WebSocket(ver.webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r));
    let id = 0; const pending = new Map();
    ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); } };
    const send = (method, params = {}, sessionId) => new Promise((res, rej) => { const i = ++id; pending.set(i, (d) => (d.error ? rej(new Error(JSON.stringify(d.error))) : res(d.result))); ws.send(JSON.stringify({ id: i, method, params, sessionId })); });
    const { targetId } = await send("Target.createTarget", { url: "about:blank" });
    const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
    const S = (m, p) => send(m, p, sessionId);
    await S("Page.enable");
    await S("Emulation.setDeviceMetricsOverride", { width: W, height: 844, deviceScaleFactor: 1, mobile: W < 700 });
    await S("Page.navigate", { url }); await sleep(3500);
    const r = await S("Runtime.evaluate", { expression: code, returnByValue: true, awaitPromise: true });
    console.log(JSON.stringify(r.result.value !== undefined ? r.result.value : r, null, 1));
    ws.close();
  } finally { chrome.kill("SIGKILL"); try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) {} }
})().catch((e) => { console.error("FAILED", e.message); process.exit(1); });
