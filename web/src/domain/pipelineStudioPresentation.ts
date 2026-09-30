/* Copyright 2026 Aaron John Schlosser, PhD. */
// UI-only derivation for Pipeline Studio. Server-owned workflow semantics stay in
// pipelineWorkflows.ts and pipelinePresentation.ts; nothing here decides what a pipeline may do.
import { pipelineKey } from "./pipelinePresentation";
import { purposeById } from "./pipelineWorkflows";
import type {
  PipelineAssignment,
  PipelineCatalog,
  PipelineDefinition,
  PipelineOperationalMetrics,
  PipelinePurpose,
  ResearchPipelineComparisonEvidence,
  ResearchPipelineComparisonResult,
} from "../types/pipelines";

export type StudioTone = "neutral" | "info" | "success" | "warning" | "danger";

export function pipelineStatusTone(status: PipelineDefinition["status"]): StudioTone {
  if (status === "active") return "success";
  if (status === "disabled") return "warning";
  return "neutral";
}

export function pipelineRuntimeTone(pipeline: Pick<PipelineDefinition, "runtime_support">) {
  return pipeline.runtime_support?.supported ? "success" : "warning";
}

export function pipelineValidationTone(pipeline: Pick<PipelineDefinition, "validation">) {
  return pipeline.validation && !pipeline.validation.valid ? "danger" : "success";
}

export function pipelineAssignmentTone(assigned: boolean): StudioTone {
  return assigned ? "info" : "neutral";
}

export function pipelineRunTone(status: string): StudioTone {
  switch (status) {
    case "completed":
      return "success";
    case "running":
      return "info";
    case "failed":
    case "timed_out":
      return "danger";
    case "unavailable":
    case "cancelled":
      return "warning";
    default:
      return "neutral";
  }
}

export interface PipelineVersionGroup {
  pipelineId: string;
  displayName: string;
  category: string;
  purpose: string;
  /** Newest first. */
  versions: PipelineDefinition[];
  assignedVersion: PipelineDefinition | null;
  latestVersion: PipelineDefinition;
  /** The version a click on the group selects. */
  selectedVersion: PipelineDefinition | null;
}

/** Whether `pipeline` is the version its purpose's consuming feature currently runs. */
export function isAssignedVersion(
  pipeline: Pick<PipelineDefinition, "pipeline_id" | "version">,
  assignments: PipelineAssignment[],
) {
  return assignments.some(
    (item) =>
      item.pipeline_id === pipeline.pipeline_id && item.pipeline_version === pipeline.version,
  );
}

/** Assigned version, else highest active executable version, else the latest. */
export function preferredVersionForGroup(
  versions: PipelineDefinition[],
  assignments: PipelineAssignment[],
) {
  const ordered = [...versions].sort((a, b) => b.version - a.version);
  return (
    ordered.find((item) => isAssignedVersion(item, assignments)) ||
    ordered.find((item) => item.status === "active" && item.runtime_support?.supported) ||
    ordered[0] ||
    null
  );
}

/** Group immutable versions by `pipeline_id`, keeping first-seen order of pipelines. */
export function groupPipelineVersions(
  pipelines: PipelineDefinition[],
  assignments: PipelineAssignment[],
  purposes: PipelinePurpose[],
): PipelineVersionGroup[] {
  const byId = new Map<string, PipelineDefinition[]>();
  for (const pipeline of pipelines) {
    const list = byId.get(pipeline.pipeline_id);
    if (list) list.push(pipeline);
    else byId.set(pipeline.pipeline_id, [pipeline]);
  }
  return [...byId.entries()].map(([pipelineId, list]) => {
    const versions = [...list].sort((a, b) => b.version - a.version);
    const latestVersion = versions[0];
    return {
      pipelineId,
      displayName: latestVersion.name,
      category: purposeById(purposes, latestVersion.purpose)?.category || "",
      purpose: latestVersion.purpose,
      versions,
      assignedVersion: versions.find((item) => isAssignedVersion(item, assignments)) || null,
      latestVersion,
      selectedVersion: preferredVersionForGroup(versions, assignments),
    };
  });
}

/**
 * Fallback when the requested pipeline is missing: the assigned Research pipeline, else the first
 * usable (active, executable) pipeline, else the first pipeline in the catalog.
 */
export function defaultPipelineKey(catalog: PipelineCatalog): string {
  const assignedResearch = catalog.assignments.find((item) => item.feature === "research");
  const preferred = catalog.pipelines.find(
    (item) =>
      item.pipeline_id === assignedResearch?.pipeline_id &&
      item.version === assignedResearch?.pipeline_version,
  );
  const usable = catalog.pipelines.find(
    (item) => item.status === "active" && item.runtime_support?.supported,
  );
  const fallback = preferred || usable || catalog.pipelines[0];
  return fallback ? pipelineKey(fallback) : "";
}

export interface OperationalAttentionRow {
  kind: "workflow" | "strategy";
  /** A workflow category, or a strategy ID. */
  id: string;
  executions: number;
  failures: number;
  issues: number;
  fallbacks: number;
  p95Ms: number | null;
}

/**
 * Rows of the operational metrics that show a failure, issue, or fallback, worst first: failures,
 * then issues, then fallbacks, each descending. Health is computational, not scholarly, so this
 * only reorders numbers the server already reported.
 */
export function pipelineOperationalAttention(
  metrics: Pick<PipelineOperationalMetrics, "workflows" | "strategies">,
): OperationalAttentionRow[] {
  const rows: OperationalAttentionRow[] = [
    ...(metrics.workflows || []).map((row) => ({
      kind: "workflow" as const,
      id: row.category,
      executions: row.run_count,
      failures: row.failed_count,
      issues: 0,
      fallbacks: row.fallback_run_count,
      p95Ms: row.p95_elapsed_ms ?? null,
    })),
    ...(metrics.strategies || []).map((row) => ({
      kind: "strategy" as const,
      id: row.strategy_id,
      executions: row.executions,
      failures: Number(row.status_counts?.failed || 0),
      issues: row.issue_count,
      fallbacks: row.fallback_count,
      p95Ms: row.p95_elapsed_ms ?? null,
    })),
  ];
  return rows
    .filter((row) => row.failures > 0 || row.issues > 0 || row.fallbacks > 0)
    .sort(
      (a, b) =>
        b.failures - a.failures ||
        b.issues - a.issues ||
        b.fallbacks - a.fallbacks ||
        a.id.localeCompare(b.id),
    );
}

export interface EvidenceComparisonRow {
  recordId: string;
  left: ResearchPipelineComparisonEvidence | null;
  right: ResearchPipelineComparisonEvidence | null;
  presence: "both" | "left" | "right";
}

/**
 * Align the two sides' final evidence by Record ID: records in both (in Pipeline A's rank order),
 * then A-only, then B-only. Describes where records sit; it never ranks the pipelines.
 */
export function pipelineComparisonRows(
  result: Pick<ResearchPipelineComparisonResult, "left" | "right">,
): EvidenceComparisonRow[] {
  const byRank = (a: ResearchPipelineComparisonEvidence, b: ResearchPipelineComparisonEvidence) =>
    a.rank - b.rank;
  const left = [...result.left.evidence].sort(byRank);
  const right = [...result.right.evidence].sort(byRank);
  const rightById = new Map(right.map((item) => [item.record_id, item]));
  const leftIds = new Set(left.map((item) => item.record_id));
  return [
    ...left.map((item) => {
      const match = rightById.get(item.record_id) ?? null;
      return {
        recordId: item.record_id,
        left: item,
        right: match,
        presence: match ? ("both" as const) : ("left" as const),
      };
    }),
    ...right
      .filter((item) => !leftIds.has(item.record_id))
      .map((item) => ({
        recordId: item.record_id,
        left: null,
        right: item,
        presence: "right" as const,
      })),
  ].sort((a, b) => presenceOrder(a.presence) - presenceOrder(b.presence));
}

// Array#sort is stable, so each group keeps the rank order it was built in.
function presenceOrder(presence: EvidenceComparisonRow["presence"]) {
  return presence === "both" ? 0 : presence === "left" ? 1 : 2;
}
