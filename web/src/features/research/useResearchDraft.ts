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

// A streamed, unverified draft of a running Research run's answer (docs/USER_GUIDE.md:
// "the workspace streams a live draft of the text as the model produces it"). Advisory only:
// the authoritative, source-bound answer always comes from REST once the run completes.
import { ref } from "vue";
import { realtime } from "../../realtime";
import type { GenerationEvent } from "../../realtime/protocol";

export interface ResearchDraftState {
  jobId: string;
  text: string;
  /** A delta was dropped before this point: stop appending and wait for the final REST answer. */
  gap: boolean;
  /** The stream reported its last delta; the authoritative REST answer should be available soon. */
  final: boolean;
}

export function useResearchDraft() {
  const draft = ref<ResearchDraftState | null>(null);
  let unsubscribe: (() => void) | null = null;
  let lastSeq = -1;

  function stopFollowing() {
    unsubscribe?.();
    unsubscribe = null;
  }

  /** Start (or restart) streaming the draft for one job. Replaces any previously followed job. */
  function follow(jobId: string) {
    stopFollowing();
    draft.value = { jobId, text: "", gap: false, final: false };
    lastSeq = -1;
    unsubscribe = realtime.subscribe(`job:${jobId}`, (event) => {
      if (event.type !== "llm.token" || draft.value?.jobId !== jobId) return;
      const generation = (event as GenerationEvent).payload.generation;
      if (draft.value.gap || draft.value.final) return; // already waiting for the final answer
      if (generation.gap) {
        draft.value = { ...draft.value, gap: true };
        return;
      }
      if (generation.seq <= lastSeq) return; // out-of-order or duplicate delivery
      lastSeq = generation.seq;
      draft.value = { ...draft.value, text: draft.value.text + generation.delta };
      if (generation.final) {
        draft.value = { ...draft.value, final: true };
        stopFollowing();
      }
    });
  }

  /** Stop streaming and drop the draft (an authoritative result is available, or nothing is live). */
  function clear() {
    stopFollowing();
    draft.value = null;
    lastSeq = -1;
  }

  return { draft, follow, clear };
}
