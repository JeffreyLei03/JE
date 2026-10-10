import test from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { RpcClient } = require("../electron/rpc-client.cjs");
test("JSONL decoder handles chunked Unicode, CRLF, correlations and asynchronous events", () => {
  const client = new EventEmitter();
  Object.setPrototypeOf(client, RpcClient.prototype);
  client.buffer = "";
  client.pending = new Map();
  let response;
  const events = [];
  client.on("event", (e) => events.push(e));
  client.pending.set("one", {
    resolve: (data) => (response = data),
    reject: assert.fail,
    timer: setTimeout(() => {}, 1000),
  });
  client.consume('{"type":"message_update","text":"你');
  client.consume(
    '好\u2028世界"}\r\n{"type":"response","id":"one","success":true,"data":{"ok":true}}\n',
  );
  assert.equal(events[0].text, "你好\u2028世界");
  assert.deepEqual(response, { ok: true });
  assert.equal(client.pending.size, 0);
  assert.equal(client.buffer, "");
});
