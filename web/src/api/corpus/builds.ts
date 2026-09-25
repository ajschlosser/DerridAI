/* Copyright 2026 Aaron John Schlosser, PhD. */
import { apiRequest } from "../http";
import type { CorpusBuild } from "./types";
import { LEGACY_CORPUS_BASE, legacyCorpusUrl } from "./compatibility";

export const corpusBuildsApi = {
  listBuilds: (offset = 0, limit = 50, assetId = "") =>
    apiRequest<{ items: CorpusBuild[]; total: number; offset: number; limit: number }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds?offset=${offset}&limit=${limit}${
        assetId ? `&asset_id=${encodeURIComponent(assetId)}` : ""
      }`,
    ),
  build: (buildId: string) =>
    apiRequest<CorpusBuild>(`${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}`),
  runAutonomous: (buildId: string, payload: Record<string, unknown>) =>
    apiRequest<CorpusBuild>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/autonomous/run`,
      { method: "POST", body: JSON.stringify(payload) },
    ),
  regenerateManifest: (buildId: string, payload: Record<string, unknown>) =>
    apiRequest<{ build: CorpusBuild; filled: string[] }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/manifest/regenerate`,
      { method: "POST", body: JSON.stringify(payload) },
    ),
  patchManifest: (
    buildId: string,
    changes: Record<string, unknown>,
    expectedRevision?: number,
  ) =>
    apiRequest<CorpusBuild>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/manifest`,
      {
        method: "PATCH",
        body: JSON.stringify({ changes, expected_revision: expectedRevision }),
      },
    ),
  switchProviderProfile: (buildId: string, payload: Record<string, unknown>) =>
    apiRequest<CorpusBuild>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/provider-profile`,
      { method: "PATCH", body: JSON.stringify(payload) },
    ),
  createBuild: (payload: Record<string, unknown>) =>
    apiRequest<CorpusBuild>(legacyCorpusUrl("corpus-builds"), {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  confirmManifest: (buildId: string, payload: Record<string, unknown>) =>
    apiRequest<CorpusBuild>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/confirm-manifest`,
      { method: "POST", body: JSON.stringify(payload) },
    ),
  cancel: (buildId: string) =>
    apiRequest<CorpusBuild>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/cancel`,
      {
        method: "POST",
      },
    ),
  settleMetadata: (buildId: string) =>
    apiRequest<CorpusBuild>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/settle-metadata`,
      { method: "POST" },
    ),
  resume: (buildId: string, payload: Record<string, unknown>) =>
    apiRequest<CorpusBuild>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/resume`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    ),
};
