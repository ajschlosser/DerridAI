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
  /** Package the optional in-browser Transformers.js runtime (no model weights). */
  include_transformers: boolean;
}

export interface SiteTransformersRuntime {
  version: string;
  /** True once DerridAI has downloaded and verified the runtime on this server. */
  cached: boolean;
  /** One-time download size when it is not cached yet. */
  download_bytes: number;
  /** Size added to a single-file or two-file site when the runtime is embedded. */
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
