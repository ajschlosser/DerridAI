/* Copyright 2026 Aaron John Schlosser, PhD. */
import { ApiError, apiRequest } from "./http";
import type { LanguageInfo } from "./system";

export type SiteExportFormat = "two-file" | "local-single-file" | "nginx-docker";

/** How much Record metadata a site carries: `reader` omits FieldAssertions to reduce file size. */
export type SiteRecordProfile = "complete" | "reader";

export interface SiteExportRequest {
  store: string;
  works: string[];
  title: string;
  description?: string;
  locale: string;
  languages: string[];
  export_format: SiteExportFormat;
  record_profile: SiteRecordProfile;
  /** Every export includes Transformers.js. Kept so older clients still send a value. */
  include_transformers: boolean;
  /** Copy the current collection vectors into the publication; otherwise browsers build their own index. */
  include_vectors: boolean;
  /** nginx/Docker only: same-origin /provider/ bridge target. Empty/null disables the proxy. */
  provider_proxy_upstream?: string | null;
}

export interface TransformersDownloadEvent {
  status: "progress" | "complete" | "error";
  file?: string;
  received?: number;
  file_total?: number;
  received_total?: number;
  total?: number;
  detail?: string;
}

export interface SiteTransformersRuntime {
  version: string;
  /** True once DerridAI has downloaded and verified the Transformers.js runtime on this server. */
  cached: boolean;
  /** One-time download size when it is not cached yet. */
  download_bytes: number;
  /** Size added to a single-file or two-file site when the Transformers.js runtime is embedded. */
  inline_bytes: number;
}

export interface SiteExportOptions {
  languages: LanguageInfo[];
  transformers_runtime: SiteTransformersRuntime;
}

export interface SiteExportDownload {
  blob: Blob;
  filename: string;
  publicationId: string;
  recordCount: number;
  workCount: number;
}

function filenameFromDisposition(value: string | null): string {
  const match = String(value || "").match(/filename="([^"]+)"/i);
  return match?.[1] || "derridai-research-site.zip";
}

export const sitesApi = {
  exportOptions: () => apiRequest<SiteExportOptions>("/api/sites/export-options"),
  deleteTransformersRuntime: () =>
    apiRequest<{ transformers_runtime: SiteTransformersRuntime }>(
      "/api/sites/transformers-runtime",
      {
        method: "DELETE",
      },
    ),
  async downloadTransformersRuntime(
    onProgress: (event: TransformersDownloadEvent) => void,
  ): Promise<void> {
    const response = await fetch("/api/sites/transformers-runtime", { method: "POST" });
    if (!response.ok || !response.body) {
      const text = await response.text();
      throw new ApiError(text || response.statusText, response.status, { detail: text });
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line) as TransformersDownloadEvent;
        if (event.status === "error") throw new Error(event.detail || "Download failed");
        onProgress(event);
      }
    }
  },
  async exportSite(payload: SiteExportRequest): Promise<SiteExportDownload> {
    const response = await fetch("/api/sites/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const text = await response.text();
      let detail = text || response.statusText;
      try {
        const parsed = JSON.parse(text) as { detail?: unknown };
        if (typeof parsed.detail === "string") detail = parsed.detail;
      } catch {
        // Preserve the response body when it is not JSON.
      }
      throw new ApiError(
        `HTTP ${response.status}${response.statusText ? ` ${response.statusText}` : ""} · ${detail}`,
        response.status,
        { detail },
        {
          statusText: response.statusText,
          responseBody: text,
          requestPath: "/api/sites/export",
          requestMethod: "POST",
          fullMessage: detail,
        },
      );
    }
    return {
      blob: await response.blob(),
      filename: filenameFromDisposition(response.headers.get("Content-Disposition")),
      publicationId: response.headers.get("X-DerridAI-Publication-ID") || "",
      recordCount: Number(response.headers.get("X-DerridAI-Record-Count") || 0),
      workCount: Number(response.headers.get("X-DerridAI-Work-Count") || 0),
    };
  },
};
