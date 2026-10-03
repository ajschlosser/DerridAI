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

import type { CorpusBuild } from "../../../api/corpus";
import {
  corpusCompletion,
  isWorkspaceAvailable,
  type CorpusWorkflowProgressInput,
  type CorpusWorkflowState,
  type CorpusWorkspace,
  type CorpusWorkspaceContext,
  CORPUS_WORKSPACES,
} from "./workspace";

/**
 * UI interpretation of build state only. Nothing here mutates or decides authoritative
 * domain state; it turns stage/status telemetry into words, tones and progress.
 */
export interface PresentationText {
  t: (key: string, fallback?: string) => string;
  tf: (key: string, values: Record<string, string | number>) => string;
}

export type WorkflowTone = "neutral" | "info" | "success" | "warning" | "danger";

export interface CorpusPrimaryStatus {
  label: string;
  detail: string;
  tone: WorkflowTone;
  progress?: number;
}

export interface CorpusWorkflowStep {
  id: CorpusWorkspace;
  available: boolean;
  state: CorpusWorkflowState;
}

const STAGE_EXPLANATIONS: Record<string, string> = {
  preparing: "Preparing the durable build workspace and restoring any valid checkpoints.",
  resuming: "Restoring the last valid checkpoint before continuing the interrupted build.",
  structure: "Reading source structure and establishing document-level metadata.",
  document_review: "Finalizing document-level metadata before segmentation.",
  constructing_topology:
    "Preparing conserved SourceUnits and the semantic topology used to construct Records.",
  segmenting:
    "Generating boundary candidates deterministically and asking the LLM only bounded local split/keep questions where needed.",
  constructing_records:
    "Constructing reviewable Records from conserved SourceUnits, validating topology, indexing source units, and applying deterministic cleanup.",
  document_intelligence:
    "Analysing the complete reviewed document for derived entity, coreference, and quotation structure before record-level metadata enrichment.",
  reconciling: "Finalizing topology from an earlier compatible build checkpoint.",
  enriching:
    "Enriching each constructed Record with discourse, quotation, and indexing metadata. Source text and boundaries are already preserved.",
  finalizing_review:
    "Revalidating the completed build, updating review queues, and preparing the human-review workspace.",
  review: "Automated processing is complete. Review the proposed Records.",
  ready: "All quality gates have passed. The corpus is ready to publish.",
  published: "The reviewed corpus has been finalized as JSONL and is ready to download.",
};

const STOPPED = new Set(["failed", "interrupted", "cancelled"]);
const NEEDS_ATTENTION = new Set(["blocked", "awaiting_manifest_review", "awaiting_metadata"]);

export function corpusStageLabel(stage: string, text: PresentationText): string {
  return text.t(`pdf_corpus.stage.${stage}`, String(stage || "unknown").replace(/_/g, " "));
}

export function corpusStageExplanation(stage: string, text: PresentationText): string {
  return text.t(
    `pdf_corpus.stage_help.${stage}`,
    STAGE_EXPLANATIONS[stage] || "Processing the current corpus-build stage.",
  );
}

/** The one sentence saying what the build is doing right now, from real telemetry. */
export function corpusCurrentOperation(
  build: CorpusBuild | null | undefined,
  text: PresentationText,
): string {
  if (!build) return "";
  const stage = String(build.stage || "");
  if (stage === "segmenting") {
    const total = Number(build.boundary_candidate_count || 0);
    const completed = Number(build.boundary_candidates_completed || 0);
    if (total > 0) {
      return text.tf("pdf_corpus.progress.boundary_candidates", {
        completed: Math.min(completed, total),
        total,
      });
    }
  }
  if (stage === "constructing_records") return text.t("pdf_corpus.progress.constructing_detail");
  if (stage === "document_intelligence")
    return text.t("pdf_corpus.progress.document_intelligence_detail");
  if (stage === "enriching") {
    const active = build.metadata_active_tasks || [];
    const total = Number(build.metadata_tasks_total || 0);
    const settled =
      Number(build.metadata_tasks_completed || 0) +
      Number(build.metadata_tasks_failed || 0) +
      Number(build.metadata_tasks_skipped || 0);
    if (active.length) {
      const activeRecordIds = new Set(
        active.map((item) => String(item.record_id || "")).filter(Boolean),
      );
      if (activeRecordIds.size === 1) {
        const first = active[0];
        return text.tf("pdf_corpus.progress.metadata_active", {
          record: first.record_id || "—",
          family: first.task || "metadata",
          active: Number(build.metadata_tasks_running || active.length),
          settled,
          total,
        });
      }
      // Several Records can enrich concurrently. The primary status describes the
      // queue as a whole instead of falsely implying the first array entry is current.
      return text.tf("pdf_corpus.progress.metadata_queue", {
        settled,
        total,
        running: Number(build.metadata_tasks_running || active.length),
        queued: Number(build.metadata_tasks_queued || 0),
      });
    }
    if (total > 0) {
      return text.tf("pdf_corpus.progress.metadata_queue", {
        settled,
        total,
        running: Number(build.metadata_tasks_running || 0),
        queued: Number(build.metadata_tasks_queued || 0),
      });
    }
  }
  if (stage === "finalizing_review") return text.t("pdf_corpus.progress.finalizing_review_detail");
  return "";
}

/** The single lifecycle badge: derived from stage, status and publication, not title-cased. */
export function corpusPrimaryStatus(
  build: CorpusBuild | null | undefined,
  text: PresentationText,
): CorpusPrimaryStatus {
  const lifecycle = (key: string, fallback: string) =>
    text.t(`pdf_corpus.lifecycle.${key}`, fallback);
  if (!build) {
    return {
      label: lifecycle("configuring", "Configuring"),
      detail: text.t(
        "pdf_corpus.lifecycle.configuring_detail",
        "Choose a source and configure the build.",
      ),
      tone: "neutral",
    };
  }
  const stage = String(build.stage || "");
  const status = String(build.status || "");
  const progress = Math.max(0, Math.min(1, Number(build.progress || 0)));
  const detail = corpusCurrentOperation(build, text) || corpusStageExplanation(stage, text);
  if (build.publication) {
    return {
      label: lifecycle("published", "Published"),
      detail: corpusStageExplanation("published", text),
      tone: "success",
    };
  }
  if (STOPPED.has(status)) {
    return {
      label: lifecycle("stopped", "Stopped"),
      detail: build.error || text.t("pdf_corpus.build_stopped_help"),
      tone: "danger",
    };
  }
  if (NEEDS_ATTENTION.has(status)) {
    return { label: lifecycle("needs_attention", "Needs attention"), detail, tone: "warning" };
  }
  if (status === "queued" || status === "running") {
    const enriching = stage === "enriching" || stage === "document_intelligence";
    return {
      label: enriching
        ? lifecycle("enriching", "Enriching metadata")
        : lifecycle("building", "Building"),
      detail,
      tone: "info",
      progress,
    };
  }
  if (status === "ready" || stage === "ready") {
    return {
      label: lifecycle("ready", "Ready to publish"),
      detail: corpusStageExplanation("ready", text),
      tone: "success",
    };
  }
  return {
    label: lifecycle("reviewing", "Reviewing"),
    detail: corpusStageExplanation("review", text),
    tone: "info",
  };
}

export function corpusWorkflowSteps(
  current: CorpusWorkspace,
  context: CorpusWorkspaceContext,
  progress: CorpusWorkflowProgressInput,
): CorpusWorkflowStep[] {
  const complete = corpusCompletion(progress);
  return CORPUS_WORKSPACES.map((id) => {
    const available = isWorkspaceAvailable(id, context);
    const state: CorpusWorkflowState =
      id === current
        ? "current"
        : complete[id] && (available || id === "setup")
          ? "complete"
          : available
            ? "available"
            : "unavailable";
    return { id, available, state };
  });
}

export type CorpusStageRailId = "prepare" | "structure" | "construct" | "enrich" | "finalize";
export interface CorpusStageRailItem {
  id: CorpusStageRailId;
  state: "complete" | "current" | "pending";
}
const RAIL: CorpusStageRailId[] = ["prepare", "structure", "construct", "enrich", "finalize"];
const RAIL_INDEX: Record<string, number> = {
  preparing: 0,
  resuming: 0,
  structure: 1,
  document_review: 1,
  constructing_topology: 2,
  segmenting: 2,
  constructing_records: 2,
  reconciling: 2,
  document_intelligence: 3,
  enriching: 3,
  finalizing_review: 4,
};

/** Five coarse groups of the backend pipeline stages; automated work done completes them all. */
export function corpusStageRail(build: CorpusBuild | null | undefined): CorpusStageRailItem[] {
  const stage = String(build?.stage || "");
  const done = Boolean(build?.publication) || ["review", "ready", "published"].includes(stage);
  const at = done ? RAIL.length : (RAIL_INDEX[stage] ?? -1);
  return RAIL.map((id, index) => ({
    id,
    state: index < at ? "complete" : index === at ? "current" : "pending",
  }));
}

/** Status token shared by build history, workflow status and queue state. */
export function corpusStatusTone(build: Pick<CorpusBuild, "status" | "publication">): WorkflowTone {
  if (build.publication) return "success";
  const status = String(build.status || "");
  if (STOPPED.has(status)) return "danger";
  if (status === "ready") return "success";
  if (status === "queued" || status === "running") return "warning";
  if (NEEDS_ATTENTION.has(status)) return "warning";
  return "neutral";
}
