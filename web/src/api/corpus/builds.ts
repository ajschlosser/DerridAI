/* Copyright 2026 Aaron John Schlosser, PhD. */
import { apiRequest } from "../http";
import type {
  CorpusBuild,
  CorpusLlmTraceEntry,
  DocumentIntelligenceRun,
  RecordSemanticMap,
  SemanticAliasDraft,
  SemanticAliasImportResult,
  SemanticAliasList,
  SemanticAliasSet,
  SemanticAliasSource,
  SemanticContentGraph,
  SemanticContentGraphView,
  SemanticGraphViewParams,
  SemanticNodeNeighborhood,
  WorkSemanticMapProjection,
} from "./types";
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
  llmTrace: (buildId: string) =>
    apiRequest<{ items: CorpusLlmTraceEntry[]; total: number }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/llm-trace`,
    ),
  llmLiveOutput: (buildId: string) =>
    apiRequest<{
      items: Array<{
        call_id: string;
        task?: string;
        provider?: string;
        model?: string;
        seq: number;
        text: string;
        gap: boolean;
      }>;
      total: number;
    }>(`${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/llm-live-output`),
  semanticContentGraph: (buildId: string) =>
    apiRequest<SemanticContentGraph>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/semantic-content-graph`,
    ),
  semanticContentGraphView: (
    buildId: string,
    params: SemanticGraphViewParams = {},
    init: { signal?: AbortSignal } = {},
  ) => {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === "" || value === null) continue;
      if (Array.isArray(value)) value.forEach((item) => query.append(key, String(item)));
      else query.set(key, String(value));
    }
    const suffix = query.toString() ? `?${query}` : "";
    return apiRequest<SemanticContentGraphView>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/semantic-content-graph/view${suffix}`,
      init,
    );
  },
  recordSemanticMapBuild: (recordId: string) =>
    apiRequest<{ build_id: string | null }>(
      `/api/records/${encodeURIComponent(recordId)}/semantic-map-build`,
    ),
  workSemanticMapBuilds: (work: string) =>
    apiRequest<{ build_ids: string[] }>(
      `/api/works/${encodeURIComponent(work)}/semantic-map-builds`,
    ),
  workSemanticMapRecords: (work: string) =>
    apiRequest<{ records: Array<{ record_id: string; build_id: string }> }>(
      `/api/works/${encodeURIComponent(work)}/semantic-map-records`,
    ),
  workSemanticMap: (work: string) =>
    apiRequest<WorkSemanticMapProjection>(
      `/api/works/${encodeURIComponent(work)}/semantic-map`,
    ),
  recordSemanticMap: (buildId: string, recordId: string) =>
    apiRequest<RecordSemanticMap>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/semantic-map`,
    ),
  semanticAliases: (buildId: string, includeRetired = false) =>
    apiRequest<SemanticAliasList>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/semantic-aliases${
        includeRetired ? "?include_retired=true" : ""
      }`,
    ),
  saveSemanticAlias: (buildId: string, draft: SemanticAliasDraft) =>
    apiRequest<SemanticAliasSet>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/semantic-aliases`,
      { method: "POST", body: JSON.stringify(draft) },
    ),
  semanticAliasSources: (buildId: string) =>
    apiRequest<{ items: SemanticAliasSource[] }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/semantic-aliases/sources`,
    ),
  importSemanticAliases: (buildId: string, sourceBuildId: string, aliasSetIds?: string[]) =>
    apiRequest<SemanticAliasImportResult>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/semantic-aliases/import`,
      {
        method: "POST",
        body: JSON.stringify({
          source_build_id: sourceBuildId,
          alias_set_ids: aliasSetIds ?? null,
        }),
      },
    ),
  retireSemanticAlias: (buildId: string, aliasSetId: string) =>
    apiRequest<SemanticAliasSet>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/semantic-aliases/${encodeURIComponent(aliasSetId)}`,
      { method: "DELETE" },
    ),
  semanticGraphNode: (buildId: string, nodeId: string) =>
    apiRequest<SemanticNodeNeighborhood>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/semantic-content-graph/nodes/${encodeURIComponent(nodeId)}`,
    ),
  rerunDocumentIntelligence: (buildId: string) =>
    apiRequest<{
      document_intelligence: DocumentIntelligenceRun;
      semantic_content_graph: SemanticContentGraph;
    }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/document-intelligence/rerun`,
      { method: "POST" },
    ),
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
  patchManifest: (buildId: string, changes: Record<string, unknown>, expectedRevision?: number) =>
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
  /** Record that these build warnings have been seen; they stay part of the build's (and corpus's) provenance. */
  acknowledgeWarnings: (buildId: string, warnings: string[]) =>
    apiRequest<Pick<CorpusBuild, "build_id" | "warning_acknowledgements">>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/warnings/acknowledge`,
      { method: "POST", body: JSON.stringify({ warnings }) },
    ),
  cancel: (buildId: string) =>
    apiRequest<CorpusBuild>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/cancel`,
      {
        method: "POST",
      },
    ),
  /** Stop after the current step, keeping checkpoints; Resume continues from there. */
  pause: (buildId: string) =>
    apiRequest<CorpusBuild>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/pause`,
      { method: "POST" },
    ),
  /** Permanently delete a finished/paused build's workspace (published JSONL files are kept). */
  deleteBuild: (buildId: string) =>
    apiRequest<{ deleted: string; had_publication: boolean }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}`,
      { method: "DELETE" },
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
