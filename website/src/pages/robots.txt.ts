import { siteUrl } from "../../site-config.mjs";
import type { APIContext } from "astro";

export function GET(_context: APIContext) {
  return new Response(
    `User-agent: *\nAllow: /\nSitemap: ${new URL("sitemap-index.xml", siteUrl)}\n`,
  );
}
