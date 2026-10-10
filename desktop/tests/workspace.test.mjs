import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, writeFile, readFile, mkdir } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const files = require("../electron/workspace.cjs");
test("workspace paths reject traversal and absolute paths", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "je-desktop-path-"));
  await writeFile(path.join(root, "note.md"), "你好");
  const file = await files.read(root, "note.md");
  assert.equal(file.text, "你好");
  await assert.rejects(files.read(root, "../outside.txt"));
  await assert.rejects(files.read(root, path.join(root, "note.md")));
});
test("save protects edits made outside the desktop", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "je-desktop-save-"));
  const filePath = path.join(root, "a.py");
  await writeFile(filePath, "original");
  const original = await files.read(root, "a.py");
  const saved = await files.save(root, "a.py", "edited", original.revision);
  assert.equal(await readFile(filePath, "utf8"), "edited");
  await writeFile(filePath, "external");
  await assert.rejects(
    files.save(root, "a.py", "overwrite", saved.revision),
    /外部修改/,
  );
  assert.equal(await readFile(filePath, "utf8"), "external");
});
test("explorer excludes generated folders and editor rejects binary data", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "je-desktop-tree-"));
  await mkdir(path.join(root, "node_modules"));
  await mkdir(path.join(root, "src"));
  await writeFile(path.join(root, "image.bin"), Buffer.from([0, 1, 2]));
  const entries = await files.list(root);
  assert.equal(entries[0].name, "src");
  assert.ok(!entries.some((e) => e.name === "node_modules"));
  await assert.rejects(files.read(root, "image.bin"), /Binary/);
});
