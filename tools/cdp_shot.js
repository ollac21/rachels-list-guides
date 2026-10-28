#!/usr/bin/env node
// Real phone-width screenshots of a built page through Chrome's DevTools protocol (Node 22+, no packages).
// Headless Chrome will not open a window narrower than ~500 px, so the width is set with
// Emulation.setDeviceMetricsOverride (a true 390 px layout viewport, mobile mode on).
//
//   node tools/cdp_shot.js <url> <outdir> <prefix> [--w 390] [--h 844] [--screens 4] [--scale 2] [--tile 2200]
//
// Writes <outdir>/<prefix>-s1..sN.png (viewport-sized screens down the page), <prefix>-full-1..k.png (the whole
// page in tiles of --tile CSS px, so every tile stays readable) and prints JSON: page height, sideways overflow.
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const args = process.argv.slice(2);
const url = args[0], outdir = args[1], prefix = args[2];
const opt = (n, d) => { const i = args.indexOf("--" + n); return i > -1 ? args[i + 1] : d; };
const W = +opt("w", 390), H = +opt("h", 844), SCREENS = +opt("screens", 4), SCALE = +opt("scale", W > 600 ? 1 : 2), TILE = +opt("tile", W > 600 ? 2400 : 1300);
const MOBILE = W < 700;
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  fs.mkdirSync(outdir, { recursive: true });
  const port = 9300 + Math.floor(Math.random() * 500);
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "cdp-"));
  const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--mute-audio",
    "--remote-debugging-port=" + port, "--user-data-dir=" + profile, "about:blank"], { stdio: "ignore" });
  let ws;
  try {
    let ver;
    for (let i = 0; i < 60; i++) { try { ver = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); break; } catch (e) { await sleep(250); } }
    ws = new WebSocket(ver.webSocketDebuggerUrl);
    await new Promise((r) => (ws.onopen = r));
    let id = 0; const pending = new Map();
    ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); } };
    const send = (method, params = {}, sessionId) => new Promise((res, rej) => {
      const i = ++id; pending.set(i, (d) => (d.error ? rej(new Error(method + ": " + JSON.stringify(d.error))) : res(d.result)));
      ws.send(JSON.stringify({ id: i, method, params, sessionId }));
    });
    const { targetId } = await send("Target.createTarget", { url: "about:blank" });
    const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
    const S = (m, p) => send(m, p, sessionId);
    await S("Page.enable");
    await S("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: SCALE, mobile: MOBILE });
    if (MOBILE) await S("Emulation.setTouchEmulationEnabled", { enabled: true });
    await S("Page.navigate", { url });
    await sleep(3500); // fonts, images, the board clip's poster
    const ev = async (expr) => (await S("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true })).result.value;
    // scroll through once so lazy video / sticky bar behave like a reader's scroll
    const total0 = await ev("document.documentElement.scrollHeight");
    for (let y = 0; y < total0; y += H) { await ev(`window.scrollTo(0,${y})`); await sleep(120); }
    await ev("window.scrollTo(0,0)"); await sleep(400);
    const total = await ev("document.documentElement.scrollHeight");
    const report = await ev(`(function(){var de=document.documentElement,w=de.clientWidth,sw=de.scrollWidth,bad=[];
      document.querySelectorAll('body *').forEach(function(e){var r=e.getBoundingClientRect();if(r.width>0&&(r.right>w+1||r.left<-1)){var cs=getComputedStyle(e);if(cs.position!=='fixed')bad.push(e.tagName.toLowerCase()+'.'+(e.className&&e.className.baseVal===undefined?String(e.className).split(' ')[0]:'')+' '+Math.round(r.left)+'..'+Math.round(r.right))}});
      return {clientWidth:w,scrollWidth:sw,overflow:sw>w,offenders:bad.slice(0,6),height:de.scrollHeight}})()`);
    const shot = async (file, clip) => {
      const r = await S("Page.captureScreenshot", clip ? { format: "png", clip: { x: 0, y: clip.y, width: W, height: clip.h, scale: 1 }, captureBeyondViewport: true } : { format: "png" });
      fs.writeFileSync(path.join(outdir, file), Buffer.from(r.data, "base64"));
    };
    const screens = [];
    for (let n = 0; n < SCREENS; n++) {
      const y = n * H; if (y >= total) break;
      await ev(`window.scrollTo(0,${y})`); await sleep(500);
      await shot(`${prefix}-s${n + 1}.png`); screens.push(`${prefix}-s${n + 1}.png`);
    }
    await ev("window.scrollTo(0,0)"); await sleep(300);
    const tiles = [];
    for (let k = 0, y = 0; y < total; k++, y += TILE) {
      await shot(`${prefix}-full-${k + 1}.png`, { y, h: Math.min(TILE, total - y) }); tiles.push(`${prefix}-full-${k + 1}.png`);
    }
    console.log(JSON.stringify({ url, w: W, ...report, screens, tiles }));
  } finally {
    try { ws && ws.close(); } catch (e) {}
    chrome.kill("SIGKILL");
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) {}
  }
})().catch((e) => { console.error("FAILED", e.message); process.exit(1); });
