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

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

// Turns an API error response into one readable message, moved verbatim from the legacy runtime.

export function fullHttpErrorDetail(
  payload: Loose | null | undefined,
  text: unknown,
  statusText: unknown = "",
) {
  const detail = payload?.detail;
  if (typeof detail === "string" && detail.trim()) return detail.trim();
  if (Array.isArray(detail)) {
    const value = detail
      .map((item) => {
        if (item && typeof item === "object") {
          const location = Array.isArray(item.loc) ? item.loc.join(".") : "";
          const message = item.msg || item.message || JSON.stringify(item);
          return location ? `${location}: ${message}` : String(message);
        }
        return String(item);
      })
      .filter(Boolean)
      .join("; ");
    if (value) return value;
  }
  if (detail && typeof detail === "object") {
    const message = detail.message || detail.error || detail.detail;
    if (message) return String(message);
    try {
      return JSON.stringify(detail);
    } catch {
      // Best effort: fall through to the default.
    }
  }
  if (text && String(text).trim()) return String(text).trim();
  return String(statusText || "Request failed");
}
