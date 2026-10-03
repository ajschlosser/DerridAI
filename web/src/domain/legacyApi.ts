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

import { fullHttpErrorDetail } from "./httpErrors";

// The legacy runtime's fetch wrapper (always-JSON, records failures for diagnostics, signals an expired session).
// Moved verbatim so domain modules can use it without importing the runtime; `api/http.ts` differs (timeouts, typed
// errors), so the two stay separate until callers migrate.
/* eslint-disable @typescript-eslint/no-explicit-any */
const HTTP_ERROR_STORAGE_KEY = "derridai.httpErrors.v1";
function storeHttpError(entry: any) {
  try {
    const current = JSON.parse(localStorage.getItem(HTTP_ERROR_STORAGE_KEY) || "[]");
    const rows = Array.isArray(current) ? current : [];
    rows.unshift(entry);
    localStorage.setItem(HTTP_ERROR_STORAGE_KEY, JSON.stringify(rows.slice(0, 50)));
    // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
  } catch {}
}
export async function api(path: string, options: any = {}): Promise<any> {
  const method = String(options.method || "GET").toUpperCase();
  let response: Response;
  try {
    response = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
  } catch (error: any) {
    const diagnostic = String(error?.message || error);
    const wrapped: any = new Error(`Network error · ${diagnostic}`);
    wrapped.diagnostic = diagnostic;
    wrapped.status = 0;
    wrapped.fullMessage = wrapped.message;
    wrapped.requestPath = String(path);
    storeHttpError({
      timestamp: new Date().toISOString(),
      method,
      path: String(path),
      status: 0,
      statusText: "Network error",
      message: wrapped.message,
      diagnostic,
      responseBody: "",
    });
    throw wrapped;
  }
  if (response.status === 401 && !String(path).startsWith("/api/auth/"))
    window.dispatchEvent(new CustomEvent("derridai-auth-expired"));
  const text = await response.text();
  let payload: any = {};
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { detail: text };
  }
  if (!response.ok) {
    const detail = fullHttpErrorDetail(payload, text, response.statusText);
    const diagnostic =
      typeof payload?.detail === "object" && !Array.isArray(payload.detail)
        ? String(payload.detail?.diagnostic || "")
        : "";
    const message = `HTTP ${response.status}${response.statusText ? ` ${response.statusText}` : ""} · ${detail}`;
    const error: any = new Error(message);
    error.status = response.status;
    error.statusText = response.statusText;
    error.diagnostic = diagnostic;
    error.payload = payload;
    error.responseBody = text;
    error.requestPath = String(path);
    error.requestMethod = method;
    error.fullMessage = message;
    storeHttpError({
      timestamp: new Date().toISOString(),
      method,
      path: String(path),
      status: response.status,
      statusText: response.statusText || "",
      message,
      diagnostic,
      responseBody: text,
    });
    throw error;
  }
  return payload;
}
