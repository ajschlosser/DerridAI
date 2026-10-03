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

import { apiRequest } from "./http";
import type {
  PipelineAnalysis,
  PipelineAssignment,
  PipelineCatalog,
  PipelineDefinition,
  PipelineOperationalMetrics,
  PipelineRunTrace,
  PipelineStrategyLatency,
  ResearchPipelineBenchmarkCase,
  ResearchPipelineBenchmarkCaseCreate,
  ResearchPipelineBenchmarkRequest,
  ResearchPipelineBenchmarkRun,
  EvidencePipelineComparisonRequest,
  EvidencePipelineComparisonResult,
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

  analyze: (pipeline: PipelineDefinition, signal?: AbortSignal) =>
    apiRequest<PipelineAnalysis>("/api/system/pipelines/analyze", {
      method: "POST",
      body: JSON.stringify(pipeline),
      signal,
    }),

  newDraft: (purpose: string) =>
    apiRequest<{ pipeline: PipelineDefinition }>("/api/system/pipelines/definitions/new-draft", {
      method: "POST",
      body: JSON.stringify({ purpose }),
    }),

  strategyLatency: () =>
    apiRequest<{ strategies: Record<string, PipelineStrategyLatency>; sampled_run_count: number }>(
      "/api/system/pipelines/strategy-latency",
    ),

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

  compareEvidenceSuggestion: (body: EvidencePipelineComparisonRequest) =>
    apiRequest<EvidencePipelineComparisonResult>(
      "/api/system/pipelines/compare/evidence-suggestion",
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    ),

  compareEvidenceRecovery: (body: EvidencePipelineComparisonRequest) =>
    apiRequest<EvidencePipelineComparisonResult>(
      "/api/system/pipelines/compare/evidence-recovery",
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    ),

  createResearchBenchmarkCase: (body: ResearchPipelineBenchmarkCaseCreate) =>
    apiRequest<{ case: ResearchPipelineBenchmarkCase; created?: boolean }>(
      "/api/system/pipelines/benchmarks/research/cases",
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    ),

  researchBenchmarkCases: (filters: { caseId?: string; limit?: number; offset?: number } = {}) => {
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

  metrics: (
    filters: { feature?: string; category?: string; owner?: string; limit?: number } = {},
  ) => {
    const query = new URLSearchParams();
    if (filters.feature) query.set("feature", filters.feature);
    if (filters.category) query.set("category", filters.category);
    if (filters.owner) query.set("owner", filters.owner);
    query.set("limit", String(filters.limit ?? 250));
    return apiRequest<PipelineOperationalMetrics>(`/api/system/pipelines/metrics?${query}`);
  },

  runs: (
    filters: {
      feature?: string;
      category?: string;
      owner?: string;
      pipelineId?: string;
      status?: string;
      query?: string;
      limit?: number;
      offset?: number;
    } = {},
  ) => {
    const query = new URLSearchParams();
    if (filters.feature) query.set("feature", filters.feature);
    if (filters.category) query.set("category", filters.category);
    if (filters.owner) query.set("owner", filters.owner);
    if (filters.pipelineId) query.set("pipeline_id", filters.pipelineId);
    if (filters.status) query.set("status", filters.status);
    if (filters.query) query.set("q", filters.query);
    query.set("limit", String(filters.limit ?? 50));
    query.set("offset", String(filters.offset ?? 0));
    return apiRequest<{ runs: PipelineRunTrace[]; limit: number; offset: number; total: number }>(
      `/api/system/pipelines/runs?${query}`,
    );
  },

  run: (runId: string) =>
    apiRequest<{ run: PipelineRunTrace }>(
      `/api/system/pipelines/runs/${encodeURIComponent(runId)}`,
    ),

  deleteRun: (runId: string) =>
    apiRequest<{ deleted: boolean; run_id: string }>(
      `/api/system/pipelines/runs/${encodeURIComponent(runId)}`,
      { method: "DELETE" },
    ),

  clearRuns: () =>
    apiRequest<{ deleted: Record<string, number> }>("/api/system/pipelines/runs/clear", {
      method: "POST",
      body: JSON.stringify({ confirm: "clear-execution-history" }),
    }),
};
