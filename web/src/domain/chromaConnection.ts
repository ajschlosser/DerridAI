/* Copyright 2026 Aaron John Schlosser, PhD. */
export type ChromaMode = "embedded" | "http";

export function parseChromaHttpUrl(url: string): {display: string; ssl: boolean} {
  const raw = String(url || "").trim();
  if (!raw) throw new Error("url-required");
  let parsed: URL;
  try { parsed = new URL(raw); } catch { throw new Error("url-invalid"); }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") throw new Error("url-invalid");
  if (parsed.username || parsed.password) throw new Error("url-credentials");
  let path = parsed.pathname.replace(/\/+$/, "");
  for (const suffix of ["/api/v2", "/api/v1", "/api"]) {
    if (path.endsWith(suffix)) path = path.slice(0, -suffix.length).replace(/\/+$/, "");
  }
  parsed.pathname = path;
  parsed.search = "";
  parsed.hash = "";
  return {display: parsed.toString().replace(/\/$/, ""), ssl: parsed.protocol === "https:"};
}

export function chromaIdentity(mode: ChromaMode, path?: string, url?: string): string {
  if (mode === "http") return url ? `Chroma server · ${url}` : "Chroma server";
  return path ? `Local Chroma · ${path}` : "Local Chroma";
}
