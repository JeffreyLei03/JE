const path = require("node:path");
const fs = require("node:fs/promises");
const { EventEmitter } = require("node:events");
const { RpcClient } = require("./rpc-client.cjs");
const files = require("./workspace.cjs");
const commands = new Set([
  "prompt",
  "abort",
  "steer",
  "follow_up",
  "get_state",
  "get_messages",
  "get_available_models",
  "set_model",
  "get_available_thinking_levels",
  "set_thinking_level",
  "get_session_stats",
  "new_session",
  "switch_session",
  "get_tree",
  "fork",
  "set_session_name",
  "compact",
  "bash",
  "desktop_reload",
  "desktop_info",
]);
class DesktopService extends EventEmitter {
  constructor(repo) {
    super();
    this.repo = repo;
    this.root = repo;
    this.rpc = null;
  }
  async open(root, trusted = false) {
    const resolved = await fs.realpath(root);
    if (!(await fs.stat(resolved)).isDirectory())
      throw new Error("请选择项目目录");
    if (this.rpc) {
      this.rpc.removeAllListeners("event");
      await this.rpc.close();
    }
    this.root = resolved;
    this.rpc = new RpcClient(this.repo, this.root, trusted);
    this.rpc.on("event", (event) => this.emit("event", event));
    return this.bootstrap();
  }
  async bootstrap() {
    if (!this.rpc) return this.open(this.repo);
    const [state, info, messages, models, stats, levels, entries] =
      await Promise.all([
        this.rpc.request("get_state"),
        this.rpc.request("desktop_info"),
        this.rpc.request("get_messages"),
        this.rpc.request("get_available_models"),
        this.rpc.request("get_session_stats"),
        this.rpc.request("get_available_thinking_levels"),
        files.list(this.root),
      ]);
    return {
      root: this.root,
      name: path.basename(this.root),
      state,
      info,
      messages: messages.messages,
      models: models.models,
      stats,
      levels: levels.levels,
      files: entries,
    };
  }
  async call(method, args = []) {
    if (!Array.isArray(args)) throw new Error("Invalid arguments");
    switch (method) {
      case "bootstrap":
        return this.bootstrap();
      case "listFiles":
        return files.list(this.root, args[0]);
      case "readFile":
        return files.read(this.root, args[0]);
      case "saveFile":
        return files.save(this.root, ...args);
      case "gitStatus":
        return files.git(this.root, ["status", "--short"]);
      case "gitDiff":
        return files.git(this.root, ["diff", "--no-ext-diff", "--"]);
      case "rpc":
        if (!commands.has(args[0])) throw new Error("Unsupported command");
        return this.rpc.request(args[0], args[1]);
      case "login":
        return this.rpc.request("desktop_login", {
          provider: args[0],
          key: args[1],
        });
      case "trustWorkspace":
        return this.open(this.root, true);
      default:
        throw new Error("Unsupported desktop operation");
    }
  }
  async close() {
    if (this.rpc) await this.rpc.close();
  }
}
module.exports = { DesktopService };
