import { siteUrl } from "../../site-config.mjs";
import type { APIContext } from "astro";

// Preserve Hugo's public sitemap URL alongside Astro's sitemap index.
export function GET(_context: APIContext) {
  return new Response(
    `<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>${new URL("sitemap-0.xml", siteUrl)}</loc></sitemap></sitemapindex>`,
    { headers: { "Content-Type": "application/xml" } },
  );
}
