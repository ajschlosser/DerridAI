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

const COMPARE_DRAFT_KEY = "compare-draft";

export interface CompareDraft {
  sourceA: "library" | "scratch";
  sourceB: "library" | "scratch";
  keyA: string;
  keyB: string;
  pasteA: string;
  pasteB: string;
  filter: "changed" | "all";
}

type PersistedCompareDraft = CompareDraft & { key: string };

/** Reads only the Compare-owned browser-local draft record. */
export async function loadCompareDraft(): Promise<CompareDraft | null> {
  try {
    const value = (await workspaceDb.get("prefs", COMPARE_DRAFT_KEY)) as
      | Partial<PersistedCompareDraft>
      | undefined;
    if (!value || value.key !== COMPARE_DRAFT_KEY) return null;
    return {
      sourceA: value.sourceA === "scratch" ? "scratch" : "library",
      sourceB: value.sourceB === "scratch" ? "scratch" : "library",
      keyA: String(value.keyA || ""),
      keyB: String(value.keyB || ""),
      pasteA: String(value.pasteA || ""),
      pasteB: String(value.pasteB || ""),
      filter: value.filter === "all" ? "all" : "changed",
    };
  } catch (error) {
    console.warn("Could not restore Compare draft", error);
    return null;
  }
}

/** Persists only Compare state; no unrelated workspace domain is serialized. */
export async function saveCompareDraft(draft: CompareDraft): Promise<void> {
  try {
    await workspaceDb.put("prefs", {
      key: COMPARE_DRAFT_KEY,
      ...draft,
    } satisfies PersistedCompareDraft);
  } catch (error) {
    console.warn("Could not persist Compare draft", error);
  }
}
