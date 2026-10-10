const fs = require("node:fs/promises");
const path = require("node:path");
const { createHash } = require("node:crypto");
const { spawn } = require("node:child_process");

const ignored = new Set([
  ".git",
  "node_modules",
  ".venv",
  "__pycache__",
  ".mypy_cache",
  ".pytest_cache",
  ".ruff_cache",
  "dist",
  "release",
  ".astro",
]);
const revision = (text) => createHash("sha256").update(text).digest("hex");
async function inside(root, relative) {
  if (typeof relative !== "string" || path.isAbsolute(relative))
    throw new Error("Expected a relative workspace path");
  const realRoot = await fs.realpath(root);
  const candidate = await fs.realpath(path.resolve(realRoot, relative));
  const rel = path.relative(realRoot, candidate);
  if (rel.startsWith(".." + path.sep) || rel === ".." || path.isAbsolute(rel))
    throw new Error("Path is outside the workspace");
  return candidate;
}
async function list(root, relative = "") {
  const target = await inside(root, relative);
  const entries = await fs.readdir(target, { withFileTypes: true });
  return entries
    .filter((e) => !ignored.has(e.name) && !e.isSymbolicLink())
    .map((e) => ({
      name: e.name,
      path: path.posix.join(relative.replaceAll("\\", "/"), e.name),
      directory: e.isDirectory(),
    }))
    .sort(
      (a, b) =>
        Number(b.directory) - Number(a.directory) ||
        a.name.localeCompare(b.name),
    );
}
async function read(root, relative) {
  const target = await inside(root, relative);
  const stat = await fs.stat(target);
  if (!stat.isFile() || stat.size > 2 * 1024 * 1024)
    throw new Error("Only text files up to 2 MB can be opened");
  const buffer = await fs.readFile(target);
  if (buffer.includes(0))
    throw new Error("Binary file cannot be opened in the editor");
  const text = buffer.toString("utf8");
  return { path: relative, text, revision: revision(text) };
}
async function save(root, relative, text, expectedRevision) {
  if (typeof text !== "string" || Buffer.byteLength(text) > 2 * 1024 * 1024)
    throw new Error("File is too large");
  const target = await inside(root, relative);
  const current = await read(root, relative);
  if (current.revision !== expectedRevision)
    throw new Error("文件已被外部修改，请重新打开后再保存。");
  await fs.writeFile(target, text, "utf8");
  return { path: relative, text, revision: revision(text) };
}
function git(root, args) {
  return new Promise((resolve) => {
    const child = spawn("git", ["-C", root, ...args], {
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let output = "";
    let error = "";
    child.stdout.on("data", (c) => {
      if (output.length < 4_000_000) output += c;
    });
    child.stderr.on("data", (c) => (error += c));
    child.on("error", () =>
      resolve({ output: "", error: "Git is unavailable" }),
    );
    child.on("close", (code) =>
      resolve({
        output: code === 0 ? output : "",
        error: code === 0 ? "" : error,
      }),
    );
  });
}
module.exports = { inside, list, read, save, git };
