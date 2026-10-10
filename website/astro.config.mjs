import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import { unified } from "@astrojs/markdown-remark";
import { admonitions } from "./src/admonitions.mjs";
import { siteUrl, siteBase, baseLinks } from "./site-config.mjs";

export default defineConfig({
  site: siteUrl.origin,
  base: siteBase,
  trailingSlash: "always",
  publicDir: "./static",
  integrations: [sitemap()],
  markdown: {
    shikiConfig: { theme: "min-dark" },
    processor: unified({ remarkPlugins: [admonitions, baseLinks] }),
  },
});
