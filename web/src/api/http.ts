export class ApiError extends Error {
  status: number;
  payload: unknown;
  constructor(message: string, status: number, payload: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
  });
  if (response.status === 401 && !path.startsWith("/api/auth/")) {
    window.dispatchEvent(new CustomEvent("derridai-auth-expired"));
  }
  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message = typeof payload === "object" && payload && "detail" in payload ? String((payload as {detail: unknown}).detail) : `${response.status} ${response.statusText}`;
    throw new ApiError(message, response.status, payload);
  }
  return payload as T;
}
