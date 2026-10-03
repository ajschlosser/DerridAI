/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

export type ChromaMode = "embedded" | "http";

export function parseChromaHttpUrl(url: string): { display: string; ssl: boolean } {
  const raw = String(url || "").trim();
  if (!raw) throw new Error("url-required");
  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    throw new Error("url-invalid");
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") throw new Error("url-invalid");
  if (parsed.username || parsed.password) throw new Error("url-credentials");
  let path = parsed.pathname.replace(/\/+$/, "");
  for (const suffix of ["/api/v2", "/api/v1", "/api"]) {
    if (path.endsWith(suffix)) path = path.slice(0, -suffix.length).replace(/\/+$/, "");
  }
  parsed.pathname = path;
  parsed.search = "";
  parsed.hash = "";
  return { display: parsed.toString().replace(/\/$/, ""), ssl: parsed.protocol === "https:" };
}

export function chromaIdentity(mode: ChromaMode, path?: string, url?: string): string {
  if (mode === "http") return url ? `Chroma server · ${url}` : "Chroma server";
  return path ? `Local Chroma · ${path}` : "Local Chroma";
}
