export const siteUrl = new URL(
  process.env.JE_SITE_URL || "https://jeffreylei03.github.io/JE/",
);
export const siteBase = siteUrl.pathname.replace(/\/$/, "") || "/";

/** @param {string} path */
export function withBase(path) {
  if (!path.startsWith("/") || path.startsWith("//")) return path;
  const base = siteBase === "/" ? "" : siteBase;
  if (base && (path === base || path.startsWith(`${base}/`))) return path;
  return `${base}${path}`;
}

export function baseLinks() {
  return (tree) => {
    function visit(node) {
      if (typeof node.url === "string") node.url = withBase(node.url);
      for (const child of node.children || []) visit(child);
    }
    visit(tree);
  };
}
