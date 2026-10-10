import { spawn } from "node:child_process";
import { readFile, unlink } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import electron from "electron";
const report = path.join(os.tmpdir(), `je-desktop-smoke-${Date.now()}.json`);
const env = { ...process.env, JE_DESKTOP_SMOKE_FILE: report };
delete env.ELECTRON_RUN_AS_NODE;
const packagedExecutable = process.argv[2];
const child = spawn(
  packagedExecutable || electron,
  packagedExecutable ? ["--smoke-test"] : [".", "--smoke-test"],
  {
    env,
    windowsHide: true,
    stdio: "inherit",
  },
);
const timeout = setTimeout(() => {
  child.kill();
  console.error("Desktop startup timed out");
  process.exitCode = 1;
}, 60000);
child.on("exit", async () => {
  clearTimeout(timeout);
  try {
    const result = JSON.parse(await readFile(report, "utf8"));
    if (!result.ready || !result.native || !result.tools.includes("read"))
      throw new Error("Native bridge did not start");
    if (packagedExecutable && !result.packaged)
      throw new Error("Packaged application did not start");
    console.log("Electron smoke test passed:", JSON.stringify(result));
    await unlink(report);
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
});
child.on("error", (error) => {
  clearTimeout(timeout);
  console.error(error.message);
  process.exitCode = 1;
});
