const { contextBridge, ipcRenderer } = require("electron");
const invoke = (method, ...args) => ipcRenderer.invoke("je:call", method, args);
contextBridge.exposeInMainWorld("je", {
  bootstrap: () => invoke("bootstrap"),
  openWorkspace: () => invoke("openWorkspace"),
  listFiles: (path) => invoke("listFiles", path),
  readFile: (path) => invoke("readFile", path),
  saveFile: (path, text, revision) => invoke("saveFile", path, text, revision),
  gitStatus: () => invoke("gitStatus"),
  gitDiff: () => invoke("gitDiff"),
  rpc: (type, fields) => invoke("rpc", type, fields),
  login: (provider, key) => invoke("login", provider, key),
  trustWorkspace: () => invoke("trustWorkspace"),
  windowControl: (action) => invoke("windowControl", action),
  onEvent: (callback) => {
    const listener = (_event, data) => callback(data);
    ipcRenderer.on("je:event", listener);
    return () => ipcRenderer.removeListener("je:event", listener);
  },
});
