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

import { workspaceDb } from "../../domain/sharedWorkspaceStorage";

const RESEARCH_COMPOSER_DRAFT_KEY = "research-composer-draft";

export interface ResearchComposerDraft {
  prompt: string;
  instructions: string;
}

// A new question and each thread's follow-up keep separate drafts, so text typed
// for one inquiry never appears as a draft in another.
function draftKey(threadId = "") {
  return threadId
    ? `${RESEARCH_COMPOSER_DRAFT_KEY}:thread:${threadId}`
    : RESEARCH_COMPOSER_DRAFT_KEY;
}

type PersistedResearchComposerDraft = ResearchComposerDraft & { key: string };

/**
 * Reads the Research composer draft independently from the monolithic workspace
 * preference snapshot. Legacy prompt/instruction values remain a fallback in
 * ResearchView until the broader preference migration is complete.
 */
export async function loadResearchComposerDraft(
  threadId = "",
): Promise<ResearchComposerDraft | null> {
  const key = draftKey(threadId);
  try {
    const value = (await workspaceDb.get("prefs", key)) as
      | Partial<PersistedResearchComposerDraft>
      | undefined;
    if (!value || value.key !== key) return null;
    return {
      prompt: String(value.prompt || ""),
      instructions: String(value.instructions || ""),
    };
  } catch (error) {
    console.warn("Could not restore Research composer draft", error);
    return null;
  }
}

/** Persists only the small Research composer draft; no other workspace domain is serialized. */
export async function saveResearchComposerDraft(
  draft: ResearchComposerDraft,
  threadId = "",
): Promise<void> {
  try {
    await workspaceDb.put("prefs", {
      key: draftKey(threadId),
      prompt: String(draft.prompt || ""),
      instructions: String(draft.instructions || ""),
    } satisfies PersistedResearchComposerDraft);
  } catch (error) {
    console.warn("Could not persist Research composer draft", error);
  }
}
