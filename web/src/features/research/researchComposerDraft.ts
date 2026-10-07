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

type PersistedResearchComposerDraft = ResearchComposerDraft & { key: string };

/**
 * Reads the Research composer draft independently from the monolithic workspace
 * preference snapshot. Legacy prompt/instruction values remain a fallback in
 * ResearchView until the broader preference migration is complete.
 */
export async function loadResearchComposerDraft(): Promise<ResearchComposerDraft | null> {
  try {
    const value = (await workspaceDb.get(
      "prefs",
      RESEARCH_COMPOSER_DRAFT_KEY,
    )) as Partial<PersistedResearchComposerDraft> | undefined;
    if (!value || value.key !== RESEARCH_COMPOSER_DRAFT_KEY) return null;
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
export async function saveResearchComposerDraft(draft: ResearchComposerDraft): Promise<void> {
  try {
    await workspaceDb.put("prefs", {
      key: RESEARCH_COMPOSER_DRAFT_KEY,
      prompt: String(draft.prompt || ""),
      instructions: String(draft.instructions || ""),
    } satisfies PersistedResearchComposerDraft);
  } catch (error) {
    console.warn("Could not persist Research composer draft", error);
  }
}
