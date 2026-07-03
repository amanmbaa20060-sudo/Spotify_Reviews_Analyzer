/**
 * Vercel build: write dashboard/static/js/config.js from API_BASE_URL.
 * Uses Node so Vercel does not treat the repo as a Python/FastAPI service.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const raw = (process.env.API_BASE_URL || process.env.RENDER_API_URL || "")
  .trim()
  .replace(/\/$/, "");
const apiBase = raw ? `${raw}/api` : "/api";
const configPath = join(root, "dashboard", "static", "js", "config.js");

mkdirSync(dirname(configPath), { recursive: true });
writeFileSync(
  configPath,
  `window.APP_CONFIG = {\n  apiBase: ${JSON.stringify(apiBase)},\n};\n`,
  "utf8",
);

const mode = apiBase.startsWith("http") ? "direct Render URL" : "same-origin /api (middleware)";
console.log(`Wrote ${configPath} with apiBase=${JSON.stringify(apiBase)} (${mode})`);

if (process.env.VERCEL && !raw) {
  console.warn(
    "WARNING: API_BASE_URL is not set on Vercel. Add it under Settings → Environment Variables.",
  );
}
