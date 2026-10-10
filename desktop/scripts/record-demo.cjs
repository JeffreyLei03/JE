// Development-only capture launcher. Runs the actual main/preload/renderer/backend.
// Inputs still come from the native desktop UI; no synthetic agent events or DOM replay.
const { app, BrowserWindow } = require("electron");
const fs = require("node:fs/promises");
const path = require("node:path");
const { performance } = require("node:perf_hooks");
app.disableHardwareAcceleration();
const directory = process.env.JE_DESKTOP_CAPTURE_DIR;
if (!directory) throw new Error("Set JE_DESKTOP_CAPTURE_DIR to a fresh capture directory");
let window;
let timer;
let busy = false;
let finished = false;
let started;
let startedAt;
const maxSeconds = Number(process.env.JE_DESKTOP_CAPTURE_SECONDS || 900);
const intervalMs = Number(process.env.JE_DESKTOP_CAPTURE_INTERVAL_MS || 250);
if (!Number.isFinite(maxSeconds) || maxSeconds < 1 || !Number.isFinite(intervalMs) || intervalMs < 33) {
  throw new Error("Invalid capture duration or interval");
}
let captureErrors = 0;
const frames = [];
app.on("browser-window-created", (_event, created) => {
  window = created;
  window.webContents.once("did-finish-load", async () => {
    await fs.mkdir(directory, { recursive: true });
    if ((await fs.readdir(directory)).length) throw new Error("Capture directory must be empty");
    started = performance.now();
    startedAt = new Date().toISOString();
    timer = setInterval(capture, intervalMs);
  });
});
async function finish() {
  if (finished) return;
  finished = true;
  clearInterval(timer);
  await fs.writeFile(path.join(directory, "frames.json"), JSON.stringify({
    renderer: "Electron webContents.capturePage", width: 1480, height: 960,
    started_at: startedAt, interval_ms: intervalMs,
    content: process.env.JE_DESKTOP_CAPTURE_HTML ? "generated HTML rendered by Chromium" : "JE Desktop",
    frames, duration_seconds: (performance.now() - started) / 1000,
  }, null, 2));
}
async function capture() {
  if (busy || finished) return;
  busy = true;
  try {
    if (window.isDestroyed() || performance.now() - started > maxSeconds * 1000 ||
        await fs.access(path.join(directory, "stop.txt")).then(() => true, () => false)) {
      await finish();
      return;
    }
    const file = `${String(frames.length).padStart(6, "0")}.png`;
    const timestamp = (performance.now() - started) / 1000;
    const image = await window.webContents.capturePage();
    await fs.writeFile(path.join(directory, file), image.resize({width:1480,height:960}).toPNG());
    frames.push({ file, timestamp });
    captureErrors = 0;
  } catch (error) {
    console.error("Capture failed:", error.message);
    captureErrors += 1;
    if (captureErrors >= 10) await finish();
  } finally {
    busy = false;
  }
}
app.on("before-quit", (event) => {
  if (started && !finished) {
    event.preventDefault();
    void finish().then(() => app.quit());
  }
});
if (process.env.JE_DESKTOP_CAPTURE_HTML) {
  app.whenReady().then(() => {
    const preview = new BrowserWindow({
      width: 1480, height: 960, title: "JE / Generated HTML",
      webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true },
    });
    preview.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
    void preview.loadFile(path.resolve(process.env.JE_DESKTOP_CAPTURE_HTML));
  });
} else {
  require("../electron/main.cjs");
}
