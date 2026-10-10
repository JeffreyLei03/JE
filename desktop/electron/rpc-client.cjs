const { spawn } = require("node:child_process");
const { EventEmitter } = require("node:events");
const path = require("node:path");
const fs = require("node:fs");

class RpcClient extends EventEmitter {
  constructor(repo, root, trusted = false) {
    super();
    this.pending = new Map();
    this.buffer = "";
    this.closed = false;
    const localPython = path.join(
      repo,
      ".venv",
      process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
    );
    const python =
      process.env.JE_PYTHON ||
      (fs.existsSync(localPython) ? localPython : "python");
    const packaged = process.env.JE_ENGINE;
    this.child = spawn(
      packaged || python,
      [
        ...(packaged ? [] : ["-u", "-m", "je_coding.desktop"]),
        "--cwd",
        root,
        ...(trusted ? ["--trusted"] : []),
      ],
      {
        cwd: repo,
        windowsHide: true,
        stdio: ["pipe", "pipe", "pipe"],
        env: {
          ...process.env,
          PYTHONPATH: path.join(repo, "src"),
          PYTHONUTF8: "1",
          JE_NO_UPDATE_CHECK: "1",
        },
      },
    );
    this.child.stdout.setEncoding("utf8");
    this.child.stderr.setEncoding("utf8");
    this.child.stdout.on("data", (chunk) => this.consume(chunk));
    this.child.stderr.on("data", (chunk) =>
      this.emit("event", { type: "desktop_diagnostic", text: chunk }),
    );
    this.child.on("error", (error) => this.fail(error));
    this.child.stdin.on("error", (error) => this.fail(error));
    this.child.on("close", (code) => {
      this.closed = true;
      this.fail(new Error(`JE 后端已退出 (${code})`));
      this.emit("event", { type: "desktop_disconnected" });
    });
  }
  consume(chunk) {
    this.buffer += chunk;
    if (Buffer.byteLength(this.buffer) > 16 * 1024 * 1024) {
      this.fail(new Error("RPC frame exceeds limit"));
      this.child.kill();
      return;
    }
    let index;
    while ((index = this.buffer.indexOf("\n")) >= 0) {
      const line = this.buffer.slice(0, index).replace(/\r$/, "");
      this.buffer = this.buffer.slice(index + 1);
      if (!line) continue;
      let record;
      try {
        record = JSON.parse(line);
      } catch {
        this.fail(new Error("Invalid JE RPC response"));
        continue;
      }
      if (record.type === "response") {
        const waiting = this.pending.get(record.id);
        if (!waiting) continue;
        this.pending.delete(record.id);
        clearTimeout(waiting.timer);
        record.success
          ? waiting.resolve(record.data)
          : waiting.reject(new Error(record.error || "JE command failed"));
      } else this.emit("event", record);
    }
  }
  request(type, fields = {}) {
    if (this.closed) return Promise.reject(new Error("JE 后端未连接"));
    return new Promise((resolve, reject) => {
      const id = require("node:crypto").randomUUID();
      const timer = setTimeout(
        () => {
          this.pending.delete(id);
          reject(new Error(`JE command timed out: ${type}`));
        },
        type === "bash" || type === "compact" ? 180000 : 45000,
      );
      this.pending.set(id, { resolve, reject, timer });
      this.child.stdin.write(JSON.stringify({ ...fields, id, type }) + "\n");
    });
  }
  fail(error) {
    for (const item of this.pending.values()) {
      clearTimeout(item.timer);
      item.reject(error);
    }
    this.pending.clear();
  }
  async close() {
    if (this.closed) return;
    try {
      await this.request("abort");
    } catch {}
    this.child.stdin.end();
    const timer = setTimeout(() => this.child.kill(), 3000);
    timer.unref();
    this.child.once("close", () => clearTimeout(timer));
    this.closed = true;
    this.fail(new Error("Workspace closed"));
  }
}
module.exports = { RpcClient };
