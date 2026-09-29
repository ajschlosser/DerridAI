/* Copyright 2026 Aaron John Schlosser, PhD. */

import { apiRequest } from "./http";
import type {
  PipelineAssignment,
  PipelineCatalog,
  PipelineDefinition,
  PipelineOperationalMetrics,
  PipelineRunTrace,
  ResearchPipelineBenchmarkCase,
  ResearchPipelineBenchmarkCaseCreate,
  ResearchPipelineBenchmarkRequest,
  ResearchPipelineBenchmarkRun,
  ResearchPipelineComparisonRequest,
  ResearchPipelineComparisonResult,
  PipelineValidationResponse,
  ResearchPipelineOptions,
} from "../types/pipelines";

export const pipelinesApi = {
  catalog: () => apiRequest<PipelineCatalog>("/api/system/pipelines"),

  researchOptions: () =>
    apiRequest<ResearchPipelineOptions>("/api/system/pipelines/research-options"),

  validate: (pipeline: PipelineDefinition) =>
    apiRequest<PipelineValidationResponse>("/api/system/pipelines/validate", {
      method: "POST",
      body: JSON.stringify(pipeline),
    }),

  cloneDraft: (pipelineId: string, version: number) =>
    apiRequest<{ pipeline: PipelineDefinition }>(
      `/api/system/pipelines/definitions/${encodeURIComponent(pipelineId)}/${version}/clone-draft`,
      { method: "POST" },
    ),

  createDefinition: (pipeline: PipelineDefinition) =>
    apiRequest<{
      pipeline: PipelineDefinition;
      validation: PipelineValidationResponse["validation"];
    }>("/api/system/pipelines/definitions", {
      method: "POST",
      body: JSON.stringify(pipeline),
    }),

  setAssignment: (assignment: PipelineAssignment) =>
    apiRequest<{ assignment: PipelineAssignment }>(
      `/api/system/pipelines/assignments/${encodeURIComponent(assignment.feature)}`,
      {
        method: "PUT",
        body: JSON.stringify(assignment),
      },
    ),

  resetAssignment: (feature: string) =>
    apiRequest<{ deleted: boolean; resolved?: Record<string, unknown> | null }>(
      `/api/system/pipelines/assignments/${encodeURIComponent(feature)}`,
      { method: "DELETE" },
    ),

  resolved: (feature: string) =>
    apiRequest<Record<string, unknown>>(
      `/api/system/pipelines/resolved/${encodeURIComponent(feature)}`,
    ),

  compareResearch: (body: ResearchPipelineComparisonRequest) =>
    apiRequest<ResearchPipelineComparisonResult>("/api/system/pipelines/compare/research", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  createResearchBenchmarkCase: (body: ResearchPipelineBenchmarkCaseCreate) =>
    apiRequest<{ case: ResearchPipelineBenchmarkCase; created?: boolean }>(
      "/api/system/pipelines/benchmarks/research/cases",
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    ),

  researchBenchmarkCases: (
    filters: { caseId?: string; limit?: number; offset?: number } = {},
  ) => {
    const query = new URLSearchParams();
    if (filters.caseId) query.set("case_id", filters.caseId);
    query.set("limit", String(filters.limit ?? 100));
    query.set("offset", String(filters.offset ?? 0));
    return apiRequest<{
      cases: ResearchPipelineBenchmarkCase[];
      limit: number;
      offset: number;
    }>(`/api/system/pipelines/benchmarks/research/cases?${query}`);
  },

  researchBenchmarkCase: (caseId: string, version: number) =>
    apiRequest<{ case: ResearchPipelineBenchmarkCase }>(
      `/api/system/pipelines/benchmarks/research/cases/${encodeURIComponent(caseId)}/${version}`,
    ),

  runResearchBenchmark: (body: ResearchPipelineBenchmarkRequest) =>
    apiRequest<{ benchmark: ResearchPipelineBenchmarkRun }>(
      "/api/system/pipelines/benchmarks/research",
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    ),

  benchmarks: (filters: { caseId?: string; limit?: number; offset?: number } = {}) => {
    const query = new URLSearchParams();
    if (filters.caseId) query.set("case_id", filters.caseId);
    query.set("limit", String(filters.limit ?? 50));
    query.set("offset", String(filters.offset ?? 0));
    return apiRequest<{
      benchmarks: ResearchPipelineBenchmarkRun[];
      limit: number;
      offset: number;
    }>(`/api/system/pipelines/benchmarks?${query}`);
  },

  benchmark: (benchmarkRunId: string) =>
    apiRequest<{ benchmark: ResearchPipelineBenchmarkRun }>(
      `/api/system/pipelines/benchmarks/${encodeURIComponent(benchmarkRunId)}`,
    ),

  metrics: (filters: { feature?: string; owner?: string; limit?: number } = {}) => {
    const query = new URLSearchParams();
    if (filters.feature) query.set("feature", filters.feature);
    if (filters.owner) query.set("owner", filters.owner);
    query.set("limit", String(filters.limit ?? 250));
    return apiRequest<PipelineOperationalMetrics>(`/api/system/pipelines/metrics?${query}`);
  },

  runs: (filters: { feature?: string; owner?: string; limit?: number; offset?: number } = {}) => {
    const query = new URLSearchParams();
    if (filters.feature) query.set("feature", filters.feature);
    if (filters.owner) query.set("owner", filters.owner);
    query.set("limit", String(filters.limit ?? 50));
    query.set("offset", String(filters.offset ?? 0));
    return apiRequest<{ runs: PipelineRunTrace[]; limit: number; offset: number }>(
      `/api/system/pipelines/runs?${query}`,
    );
  },

  run: (runId: string) =>
    apiRequest<{ run: PipelineRunTrace }>(
      `/api/system/pipelines/runs/${encodeURIComponent(runId)}`,
    ),
};
