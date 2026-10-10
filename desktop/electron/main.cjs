const {
  app,
  BrowserWindow,
  ipcMain,
  dialog,
  protocol,
  net,
} = require("electron");
const path = require("node:path");
const fs = require("node:fs/promises");
const { pathToFileURL } = require("node:url");
const { inside } = require("./workspace.cjs");
const { DesktopService } = require("./service.cjs");
protocol.registerSchemesAsPrivileged([
  {
    scheme: "jeapp",
    privileges: {
      standard: true,
      secure: true,
      supportFetchAPI: true,
      stream: true,
    },
  },
]);
let window;
let service;
app.whenReady().then(async () => {
  const repo =
    process.env.JE_REPO ||
    (app.isPackaged
      ? path.join(app.getPath("userData"), "workspace")
      : path.resolve(__dirname, "../.."));
  if (app.isPackaged) await fs.mkdir(repo, { recursive: true });
  if (app.isPackaged)
    process.env.JE_ENGINE = path.join(
      process.resourcesPath,
      "engine",
      "je-engine.exe",
    );
  service = new DesktopService(repo);
  const dist = path.join(__dirname, "../dist");
  protocol.handle("jeapp", async (request) => {
    try {
      const url = new URL(request.url);
      if (url.hostname !== "app") return new Response("", { status: 403 });
      const file = await inside(
        dist,
        decodeURIComponent(url.pathname).slice(1),
      );
      return net.fetch(pathToFileURL(file).toString());
    } catch {
      return new Response("", { status: 404 });
    }
  });
  window = new BrowserWindow({
    width: 1480,
    height: 960,
    minWidth: 1060,
    minHeight: 700,
    title: "JE Desktop",
    icon: path.join(__dirname, "../assets/icon.png"),
    backgroundColor: "#f8f9fb",
    frame: false,
    show: !process.argv.includes("--smoke-test"),
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  window.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  window.webContents.on("will-navigate", (event) => event.preventDefault());
  service.on("event", (event) => {
    if (!window.isDestroyed()) window.webContents.send("je:event", event);
  });
  ipcMain.handle("je:call", async (event, method, args) => {
    if (
      event.sender !== window.webContents ||
      event.senderFrame !== window.webContents.mainFrame
    )
      throw new Error("Invalid sender");
    if (method === "openWorkspace") {
      const selected = await dialog.showOpenDialog(window, {
        properties: ["openDirectory"],
      });
      return selected.canceled ? null : service.open(selected.filePaths[0]);
    }
    if (method === "windowControl") {
      if (args[0] === "minimize") window.minimize();
      else if (args[0] === "maximize")
        window.isMaximized() ? window.unmaximize() : window.maximize();
      else if (args[0] === "close") window.close();
      return;
    }
    const result = await service.call(method, args);
    if (method === "bootstrap" && process.argv.includes("--smoke-test")) {
      await fs.writeFile(
        process.env.JE_DESKTOP_SMOKE_FILE,
        JSON.stringify({
          ready: true,
          model: result.state.model.id,
          tools: result.info.tools,
          files: result.files.length,
          native: true,
          packaged: app.isPackaged,
        }),
      );
      setTimeout(() => app.quit(), 300);
    }
    return result;
  });
  const url = process.env.JE_DESKTOP_URL;
  if (url) {
    if (url !== "http://127.0.0.1:5174")
      throw new Error("Unexpected development URL");
    window.loadURL(url);
  } else window.loadURL("jeapp://app/index.html");
});
app.on("window-all-closed", () => app.quit());
let quitting = false;
app.on("before-quit", (event) => {
  if (!quitting && service) {
    event.preventDefault();
    quitting = true;
    service.close().finally(() => app.quit());
  }
});
