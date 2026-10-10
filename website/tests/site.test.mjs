import assert from "node:assert/strict";
import { readFile, readdir, access } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { siteUrl, withBase } from "../site-config.mjs";
import { admonitions } from "../src/admonitions.mjs";

const dist = path.resolve("dist");
async function files(dir) {
  return (
    await Promise.all(
      (await readdir(dir, { withFileTypes: true })).map((entry) => {
        const file = path.join(dir, entry.name);
        return entry.isDirectory() ? files(file) : [file];
      }),
    )
  ).flat();
}

test("all Markdown routes and static hosting artifacts exist", async () => {
  for (const file of await files(path.resolve("content"))) {
    if (!file.endsWith(".md")) continue;
    const route = path
      .relative(path.resolve("content"), file)
      .split(path.sep)
      .join("/")
      .replace(/\.md$/, "")
      .replace(/(^|\/)\_index$/, "");
    await access(path.join(dist, route, "index.html"));
  }
  for (const file of [
    "404.html",
    "index.xml",
    "robots.txt",
    "sitemap-index.xml",
    "sitemap.xml",
    "install.sh",
    "install.ps1",
    "pagefind/pagefind.js",
  ])
    await access(path.join(dist, file));
});

test("built HTML contains no Hugo syntax or unresolved template values, and local links resolve", async () => {
  for (const file of (await files(dist)).filter((file) =>
    file.endsWith(".html"),
  )) {
    const html = await readFile(file, "utf8");
    assert.doesNotMatch(html, /\{\{[<%]|\{site\./, file);
    assert.ok(html.includes(`rel="canonical" href="${siteUrl.href}`), file);
    const route = "/" + path.relative(dist, file).replace(/index\.html$/, "");
    for (const match of html.matchAll(/(?:href|src)="([^"]+)"/g)) {
      const url = new URL(
        match[1].replaceAll("&amp;", "&"),
        new URL(withBase(route), siteUrl.origin),
      );
      if (url.origin !== siteUrl.origin) continue;
      const base = siteUrl.pathname.replace(/\/$/, "");
      assert.ok(
        url.pathname.startsWith(`${base}/`),
        `${file}: outside base ${url}`,
      );
      const target = decodeURIComponent(url.pathname.slice(base.length));
      const targetFile = path.join(
        dist,
        target.endsWith("/") ? `${target}index.html` : target,
      );
      await access(targetFile);
      if (url.hash && targetFile.endsWith(".html")) {
        const targetHtml = await readFile(targetFile, "utf8");
        const id = decodeURIComponent(url.hash.slice(1));
        assert.ok(
          targetHtml.includes(`id="${id}"`),
          `${file}: missing anchor ${url.href}`,
        );
      }
    }
  }
});

test("docs retain callouts, highlighting, navigation, and edit links", async () => {
  const html = await readFile(path.join(dist, "quickstart/index.html"), "utf8");
  for (const value of [
    "admonition-tip",
    "Already have a package manager?",
    "astro-code",
    "docs-sidebar",
    "docs-prevnext",
    "/edit/main/website/content/quickstart.md",
  ])
    assert.ok(html.includes(value), value);
  const home = await readFile(path.join(dist, "index.html"), "utf8");
  assert.ok(home.includes("https://github.com/JeffreyLei03/JE"));
  for (const frame of ["01-prompt.svg", "02-result.svg", "03-tools.svg"]) {
    assert.ok(
      home.includes(frame.replace(".svg", ".jpg")),
      `missing real demo frame: ${frame}`,
    );
    await access(path.join(dist, "images/demo", frame));
  }
  assert.ok(home.includes('id="demo"'));
  assert.ok(home.includes('id="engineering"'));
  const why = await readFile(path.join(dist, "why-tau/index.html"), "utf8");
  assert.ok(why.includes("MathJax"));
});

test("callout plugin preserves inline content and supports default titles", () => {
  const tree = {
    children: [
      {
        type: "blockquote",
        children: [
          {
            type: "paragraph",
            children: [
              { type: "text", value: "[!NOTE]\nHello " },
              { type: "strong", children: [{ type: "text", value: "world" }] },
            ],
          },
        ],
      },
    ],
  };
  admonitions()(tree);
  const node = tree.children[0];
  assert.equal(node.data.hName, "aside");
  assert.equal(node.children[0].children[0].value, "Note");
  assert.equal(node.children[1].children[0].value, "Hello ");
  assert.equal(node.children[1].children[1].type, "strong");
});

test("homepage search includes the complete documentation index", async () => {
  const entry = JSON.parse(
    await readFile(path.join(dist, "pagefind/pagefind-entry.json"), "utf8"),
  );
  const indexes = Object.values(entry.languages);
  assert.equal(
    indexes.length,
    1,
    "homepage and docs must share a searchable index",
  );
  const pages = (await files(dist)).filter((file) => file.endsWith(".html"));
  assert.equal(indexes[0].page_count, pages.length);
});

test("demo assets carry a real-run record without credentials", async () => {
  const directory = path.join(dist, "images/demo");
  const record = JSON.parse(
    await readFile(path.join(directory, "capture.json"), "utf8"),
  );
  assert.equal(record.renderer, "Textual App.save_screenshot");
  for (const tool of ["read", "edit", "write"])
    assert.ok(record.tools.includes(tool));
  assert.match(record.validation, /assertions passed/);
  for (const file of await files(directory)) {
    assert.doesNotMatch(
      await readFile(file, "utf8"),
      /sk-(?:proj-)?[a-zA-Z0-9_-]{20,}/,
      file,
    );
  }
});
