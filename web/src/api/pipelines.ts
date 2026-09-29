/* Copyright 2026 Aaron John Schlosser, PhD. */

import { apiRequest } from "./http";
import type {
  PipelineAssignment,
  PipelineCatalog,
  PipelineDefinition,
  PipelineRunTrace,
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
