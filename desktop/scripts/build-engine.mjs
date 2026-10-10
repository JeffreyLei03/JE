import { spawn } from "node:child_process";
import path from "node:path";
const python =
  process.env.JE_PYTHON || path.resolve("../.venv/Scripts/python.exe");
const child = spawn(
  python,
  [
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--name",
    "je-engine",
    "--paths",
    path.resolve("../src"),
    "--collect-data",
    "je_coding",
    "--collect-submodules",
    "je_ai",
    "--distpath",
    "engine-dist",
    "--workpath",
    "engine-build",
    "scripts/engine-entry.py",
  ],
  { stdio: "inherit", windowsHide: true },
);
child.on("exit", (code) => process.exit(code || 0));
child.on("error", (error) => {
  console.error(error.message);
  process.exit(1);
});
