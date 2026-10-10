import type { DesktopApi, Event } from "./types";
export const native = Boolean(window.je);
let token = "";
let tokenPromise: Promise<void> | undefined;
const base = "http://127.0.0.1:5175";
async function authenticate() {
  if (!tokenPromise)
    tokenPromise = fetch(base + "/bootstrap").then(async (r) => {
      if (!r.ok) throw new Error("浏览器预览需要启动 QA bridge");
      token = (await r.json()).token;
    });
  return tokenPromise;
}
async function invoke<T>(method: string, ...args: unknown[]): Promise<T> {
  await authenticate();
  const response = await fetch(base + "/call", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-JE-Token": token },
    body: JSON.stringify({ method, args }),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error);
  return result.data;
}
const preview: DesktopApi = {
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
  windowControl: async () => {},
  onEvent: (callback) => {
    const abort = new AbortController();
    void (async () => {
      try {
        await authenticate();
        const res = await fetch(base + "/events", {
          headers: { "X-JE-Token": token },
          signal: abort.signal,
        });
        const reader = res.body?.getReader();
        if (!reader) return;
        let buffer = "";
        const decoder = new TextDecoder();
        while (!abort.signal.aborted) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let end;
          while ((end = buffer.indexOf("\n\n")) >= 0) {
            const record = buffer.slice(0, end);
            buffer = buffer.slice(end + 2);
            if (record.startsWith("data: "))
              callback(JSON.parse(record.slice(6)) as Event);
          }
        }
      } catch (error) {
        if (!abort.signal.aborted)
          callback({ type: "desktop_disconnected", error: String(error) });
      }
    })();
    return () => abort.abort();
  },
};
export const api: DesktopApi = window.je ?? preview;
