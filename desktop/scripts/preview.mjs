// Real backend bridge for browser QA. Not included in packaged Electron builds.
import http from "node:http";
import { randomBytes } from "node:crypto";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
const require = createRequire(import.meta.url);
const { DesktopService } = require("../electron/service.cjs");
const repo = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);
const service = new DesktopService(repo);
await service.open(process.env.JE_DESKTOP_WORKSPACE || repo);
const token = randomBytes(32).toString("hex");
const listeners = new Set();
service.on("event", (data) => {
  for (const res of listeners) res.write(`data: ${JSON.stringify(data)}\n\n`);
});
const server = http.createServer(async (req, res) => {
  if (
    req.headers.host !== "127.0.0.1:5175" ||
    req.headers.origin !== "http://127.0.0.1:5174"
  ) {
    res.writeHead(403).end();
    return;
  }
  res.setHeader("Access-Control-Allow-Origin", "http://127.0.0.1:5174");
  res.setHeader("Vary", "Origin");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type,X-JE-Token");
  if (req.method === "OPTIONS") {
    res.writeHead(204).end();
    return;
  }
  if (req.url === "/bootstrap" && req.method === "GET") {
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({ token }));
    return;
  }
  if (req.headers["x-je-token"] !== token) {
    res.writeHead(403).end();
    return;
  }
  if (req.url === "/events") {
    res.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
    });
    res.write(": connected\n\n");
    listeners.add(res);
    req.on("close", () => listeners.delete(res));
    return;
  }
  if (req.url !== "/call" || req.method !== "POST") {
    res.writeHead(404).end();
    return;
  }
  let body = "";
  for await (const chunk of req) {
    body += chunk;
    if (body.length > 3 * 1024 * 1024) {
      res.writeHead(413).end();
      return;
    }
  }
  try {
    const { method, args } = JSON.parse(body);
    if (
      ["login", "trustWorkspace", "openWorkspace", "windowControl"].includes(
        method,
      )
    )
      throw new Error("请在 Electron 桌面窗口使用此功能");
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({ data: await service.call(method, args) }));
  } catch (error) {
    res
      .writeHead(400, { "Content-Type": "application/json" })
      .end(JSON.stringify({ error: error.message }));
  }
});
server.listen(5175, "127.0.0.1", () =>
  console.log("JE browser QA bridge: 127.0.0.1:5175"),
);
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, async () => {
    for (const res of listeners) res.end();
    await service.close();
    server.close();
    process.exit();
  });
