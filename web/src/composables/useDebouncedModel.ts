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

import { onBeforeUnmount, ref, watch, type Ref } from "vue";

/**
 * A local draft for a text input whose committed value is expensive to react to (a server
 * query per change). Typing updates `draft` immediately; the committed model follows after
 * `delayMs` of quiet, or at once through `flush()` (Enter, clear). External changes to the
 * model replace the draft so programmatic updates are never overwritten by stale typing.
 */
export function useDebouncedModel(
  model: Ref<string>,
  commit: (value: string) => void,
  delayMs = 300,
) {
  const draft = ref(model.value);
  let timer: ReturnType<typeof setTimeout> | undefined;

  function cancel() {
    if (timer !== undefined) clearTimeout(timer);
    timer = undefined;
  }
  function flush() {
    cancel();
    if (draft.value !== model.value) commit(draft.value);
  }
  function onInput(value: string) {
    draft.value = value;
    cancel();
    // Clearing is an explicit reset, not a refinement: apply it without waiting.
    if (!value) return flush();
    timer = setTimeout(flush, delayMs);
  }

  watch(model, (value) => {
    cancel();
    draft.value = value;
  });
  onBeforeUnmount(cancel);

  return { draft, onInput, flush };
}
