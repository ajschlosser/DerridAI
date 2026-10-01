/* Copyright 2026 Aaron John Schlosser, PhD. */
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
