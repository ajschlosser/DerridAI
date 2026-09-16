export interface StoredHttpError {
  timestamp: string;
  method: string;
  path: string;
  status: number;
  statusText: string;
  message: string;
  responseBody: string;
}

const HTTP_ERROR_STORAGE_KEY = "derridai.httpErrors.v1";

export class ApiError extends Error {
  status: number;
  statusText: string;
  payload: unknown;
  responseBody: string;
  requestPath: string;
  requestMethod: string;
  fullMessage: string;
  constructor(message: string, status: number, payload: unknown = null, context: Partial<ApiError> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.statusText = String(context.statusText || "");
    this.payload = payload;
    this.responseBody = String(context.responseBody || "");
    this.requestPath = String(context.requestPath || "");
    this.requestMethod = String(context.requestMethod || "GET");
    this.fullMessage = String(context.fullMessage || message);
  }
}

function storeHttpError(entry: StoredHttpError) {
  try {
    const parsed = JSON.parse(localStorage.getItem(HTTP_ERROR_STORAGE_KEY) || "[]");
    const rows = Array.isArray(parsed) ? parsed : [];
    rows.unshift(entry);
    localStorage.setItem(HTTP_ERROR_STORAGE_KEY, JSON.stringify(rows.slice(0, 50)));
  } catch { /* diagnostics must never break the request path */ }
}

export function recentHttpErrors(): StoredHttpError[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(HTTP_ERROR_STORAGE_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch { return []; }
}

function fullDetail(payload: unknown, text: string, statusText: string): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as {detail?: unknown}).detail;
    if (typeof detail === "string" && detail.trim()) return detail.trim();
    if (Array.isArray(detail)) return detail.map(item => {
      if (item && typeof item === "object") {
        const row = item as {loc?: unknown; msg?: unknown; message?: unknown};
        const location = Array.isArray(row.loc) ? row.loc.join(".") : "";
        const message = row.msg ?? row.message ?? JSON.stringify(item);
        return location ? `${location}: ${String(message)}` : String(message);
      }
      return String(item);
    }).filter(Boolean).join("; ");
    if (detail && typeof detail === "object") {
      const row = detail as {message?: unknown; error?: unknown; detail?: unknown};
      if (row.message ?? row.error ?? row.detail) return String(row.message ?? row.error ?? row.detail);
      try { return JSON.stringify(detail); } catch { /* no-op */ }
    }
  }
  return text.trim() || statusText || "Request failed";
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = String(init.method || "GET").toUpperCase();
  let response: Response;
  try {
    const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
    const headers = new Headers(init.headers || {});
    if (!isFormData && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    response = await fetch(path, {
      ...init,
      headers,
    });
  } catch (cause) {
    const detail = cause instanceof Error ? cause.message : String(cause);
    const message = `Network error · ${detail}`;
    storeHttpError({timestamp: new Date().toISOString(), method, path, status: 0, statusText: "Network error", message, responseBody: ""});
    throw new ApiError(message, 0, null, {requestPath: path, requestMethod: method, fullMessage: message});
  }

  const text = await response.text();
  let payload: unknown = {};
  try { payload = text ? JSON.parse(text) : {}; }
  catch { payload = {detail: text}; }

  if (!response.ok) {
    const detail = fullDetail(payload, text, response.statusText);
    const message = `HTTP ${response.status}${response.statusText ? ` ${response.statusText}` : ""} · ${detail}`;
    storeHttpError({timestamp: new Date().toISOString(), method, path, status: response.status, statusText: response.statusText, message, responseBody: text});
    throw new ApiError(message, response.status, payload, {
      statusText: response.statusText,
      responseBody: text,
      requestPath: path,
      requestMethod: method,
      fullMessage: message,
    });
  }
  return payload as T;
}
