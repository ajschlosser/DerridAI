/* Copyright 2026 Aaron John Schlosser, PhD. */
import { onBeforeUnmount, ref } from "vue";
import { corpusCaptureApi, type CorpusCapture } from "../api/corpus";

/**
 * Keep one capture current while its background job runs: `GET /captures/{id}` is polled only
 * while `active_job` is set, and polling stops as soon as the job finishes or the owner unmounts.
 * Callers refresh their own dependent data (candidates, source rows) from `onSettled`, so a
 * finished job never triggers a refetch of the whole Sources list.
 */
export function useCapturePolling(
  options: {
    intervalMs?: number;
    onUpdate?: (capture: CorpusCapture) => void;
    onSettled?: (capture: CorpusCapture) => void;
  } = {},
) {
  const capture = ref<CorpusCapture | null>(null);
  const error = ref("");
  const interval = options.intervalMs ?? 1500;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let stopped = false;

  function clear() {
    if (timer !== undefined) clearTimeout(timer);
    timer = undefined;
  }

  function accept(next: CorpusCapture) {
    const wasActive = Boolean(capture.value?.active_job);
    capture.value = next;
    options.onUpdate?.(next);
    if (next.active_job) schedule();
    else if (wasActive) options.onSettled?.(next);
  }

  function schedule() {
    clear();
    if (stopped) return;
    timer = setTimeout(() => void load(), interval);
  }

  async function load(captureId = capture.value?.capture_id) {
    if (!captureId) return null;
    try {
      const next = await corpusCaptureApi.getCapture(captureId);
      error.value = "";
      accept(next);
      return next;
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : String(cause);
      // A transient failure keeps polling a running job; a stopped one waits for the user.
      if (capture.value?.active_job) schedule();
      return null;
    }
  }

  function stop() {
    stopped = true;
    clear();
  }

  function reset() {
    clear();
    stopped = false;
    capture.value = null;
    error.value = "";
  }

  onBeforeUnmount(stop);
  return { capture, error, load, accept, stop, reset };
}
