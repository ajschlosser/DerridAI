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

/** The four top-level Corpus Builder workspaces: Setup → Build → Review → Publish. */
export type CorpusWorkspace = "setup" | "build" | "review" | "publish";

export const CORPUS_WORKSPACES: readonly CorpusWorkspace[] = [
  "setup",
  "build",
  "review",
  "publish",
] as const;

export interface CorpusWorkspaceContext {
  hasBuild: boolean;
  /** Records (and their topology) exist, so they can be reviewed and published. */
  hasRecordTopology: boolean;
}

export type CorpusWorkflowState = "complete" | "current" | "available" | "unavailable";

export function parseCorpusWorkspace(value: unknown): CorpusWorkspace | "" {
  const text = String(Array.isArray(value) ? value[0] : (value ?? ""));
  return (CORPUS_WORKSPACES as readonly string[]).includes(text) ? (text as CorpusWorkspace) : "";
}

/**
 * Whether a workspace can be entered. Publish does not require a publishable build:
 * it is where publication blockers are inspected and repaired.
 */
export function isWorkspaceAvailable(
  workspace: CorpusWorkspace,
  context: CorpusWorkspaceContext,
): boolean {
  if (workspace === "setup") return true;
  if (workspace === "build") return context.hasBuild;
  return context.hasBuild && context.hasRecordTopology;
}

/** The requested workspace when it is available, otherwise the fallback. */
export function resolveWorkspace(
  requested: CorpusWorkspace | "",
  context: CorpusWorkspaceContext,
  fallback: CorpusWorkspace,
): CorpusWorkspace {
  return requested && isWorkspaceAvailable(requested, context) ? requested : fallback;
}

export interface CorpusReviewRouteState {
  buildId: string;
  queue: string;
  recordId: string;
}

/**
 * The address a workspace should have for the current review state. Build/queue/record are
 * mirrored into the query only while reviewing: an explicit non-review `?workspace=` owns a URL
 * without them (see `switchWorkspace`), so writing them back would re-add state the reviewer
 * deliberately left and make Back/Forward step through addresses they never visited.
 */
export function syncedReviewQuery(
  current: Record<string, unknown>,
  state: CorpusReviewRouteState,
): Record<string, unknown> {
  const query: Record<string, unknown> = { ...current, build: state.buildId, queue: state.queue };
  if (state.recordId) query.record = state.recordId;
  else delete query.record;
  const requested = parseCorpusWorkspace(current.workspace);
  if (requested && requested !== "review") {
    delete query.record;
    delete query.queue;
  }
  return query;
}

export interface CorpusWorkflowProgressInput {
  build: CorpusBuild | null;
  hasSource: boolean;
  setupCanStart: boolean;
  hasRecordTopology: boolean;
}

/** Automated processing has produced a reviewable (or later) build. */
export function isAutomatedProcessingDone(build: CorpusBuild | null): boolean {
  if (!build) return false;
  if (build.publication) return true;
  return (
    ["review", "ready", "published"].includes(String(build.stage || "")) ||
    ["ready", "awaiting_review"].includes(String(build.status || ""))
  );
}

/** Which workflow stages are complete. Completion never controls navigability. */
export function corpusCompletion(
  input: CorpusWorkflowProgressInput,
): Record<CorpusWorkspace, boolean> {
  const build = input.build;
  const recordCount = Number(build?.record_count || 0);
  return {
    setup: input.hasSource && input.setupCanStart,
    build: isAutomatedProcessingDone(build),
    review:
      recordCount > 0 &&
      Number(
        build?.publication_readiness?.records_pending ??
          Math.max(
            0,
            recordCount - Number(build?.accepted_count || 0) - Number(build?.rejected_count || 0),
          ),
      ) === 0,
    publish: Boolean(build?.publication),
  };
}
