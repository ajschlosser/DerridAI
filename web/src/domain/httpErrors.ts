/* Copyright 2026 Aaron John Schlosser, PhD. */
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
