const { app, BrowserWindow } = require("electron");
const path = require("node:path");
const fs = require("node:fs/promises");

app.disableHardwareAcceleration();

process.env.JE_REPO = "D:/projects/tmp/je-synthwave-demo";
process.env.JE_PYTHON = "D:/projects/JE/.venv/Scripts/python.exe";
process.env.PYTHONPATH = "D:/projects/JE/src";

const captureDir = "D:/projects/tmp/je-synthwave-desktop-capture";

let window;
let frameCount = 0;

async function snap(dir) {
  const file = `${String(frameCount++).padStart(6, "0")}.png`;
  const img = await window.webContents.capturePage();
  await fs.writeFile(path.join(dir, file), img.resize({ width: 1480, height: 960 }).toPNG());
}

async function safeEval(code) {
  try {
    return await window.webContents.executeJavaScript(
      `(async () => { try { ${code} } catch(e) { console.error('Renderer eval error:', e); return null; } })()`
    );
  } catch (err) {
    console.error("safeEval error:", err.message);
    return null;
  }
}

app.on("browser-window-created", (_event, created) => {
  window = created;
  window.webContents.on("console-message", (_event, level, message) => {
    console.log("[Renderer Console]", message);
  });

  window.webContents.once("did-finish-load", async () => {
    console.log("Window loaded, starting capture sequence...");
    await fs.rm(captureDir, { recursive: true, force: true });
    await fs.mkdir(captureDir, { recursive: true });

    // Wait 2s for initial bootstrap
    await new Promise((r) => setTimeout(r, 2000));

    // 1. Switch to synthwave session
    console.log("Phase 1: Switching to synthwave session...");
    await safeEval(`
      for (let i = 0; i < 30; i++) {
        const target = document.querySelector('.session-list .session-row');
        if (target) {
          console.log('Found session-list row, clicking:', target.innerText);
          target.click();
          return;
        }
        await new Promise(r => setTimeout(r, 150));
      }
      console.error('Timed out searching for session-list row');
    `);
    await new Promise((r) => setTimeout(r, 3000));

    // Phase 1: Chat top showing User Prompt (15 frames)
    console.log("Capturing Phase 1: User Prompt...");
    await safeEval(`
      const el = document.querySelector('.messages');
      if (el) el.scrollTop = 0;
    `);
    for (let i = 0; i < 15; i++) {
      await snap(captureDir);
      await new Promise((r) => setTimeout(r, 120));
    }

    // Phase 2: Scroll down to agent reasoning & tools (25 frames)
    console.log("Capturing Phase 2: Agent reasoning and tools...");
    for (let i = 0; i < 25; i++) {
      await safeEval(`
        const el = document.querySelector('.messages');
        if (el) el.scrollTop += 60;
      `);
      await snap(captureDir);
      await new Promise((r) => setTimeout(r, 120));
    }

    // Phase 3: Open file tree and click index.html (15 frames)
    console.log("Capturing Phase 3: Open file tree and index.html...");
    await safeEval(`
      const activityButtons = document.querySelectorAll('.activity-bar button');
      if (activityButtons.length > 1) activityButtons[1].click();
    `);
    await new Promise((r) => setTimeout(r, 600));

    await safeEval(`
      const fileEntries = document.querySelectorAll('.file-row, .entry-row, button');
      for (const fe of fileEntries) {
        if (fe.innerText && fe.innerText.includes('index.html')) {
          fe.click();
          break;
        }
      }
    `);
    await new Promise((r) => setTimeout(r, 1500));

    for (let i = 0; i < 15; i++) {
      await snap(captureDir);
      await new Promise((r) => setTimeout(r, 120));
    }

    // Phase 4: Enable split view and scroll Monaco editor (25 frames)
    console.log("Capturing Phase 4: Split view and Monaco editor...");
    await safeEval(`
      const buttons = Array.from(document.querySelectorAll('button'));
      const splitBtn = buttons.find(b => b.innerHTML.includes('lucide-split-square-horizontal') || b.title === '分栏' || b.getAttribute('aria-label')?.includes('分栏'));
      if (splitBtn) splitBtn.click();
    `);
    await new Promise((r) => setTimeout(r, 1500));

    for (let i = 0; i < 25; i++) {
      await safeEval(`
        const editorDom = document.querySelector('.monaco-editor .monaco-scrollable-element');
        if (editorDom) editorDom.scrollTop += 45;
      `);
      await snap(captureDir);
      await new Promise((r) => setTimeout(r, 120));
    }

    console.log(`Successfully completed! Captured ${frameCount} frames.`);
    app.quit();
  });
});

require("../desktop/electron/main.cjs");
