/* Copyright 2026 Aaron John Schlosser, PhD. */
import { onBeforeUnmount, ref } from "vue";
import { followResource } from "../realtime/follow";
import { corpusCaptureApi, type CorpusCapture } from "../api/corpus";

/**
 * Keep one capture current while its background job runs: the job's realtime events trigger a
 * `GET /captures/{id}` read (REST fallback only while the socket is down), and following stops as
 * soon as the job finishes or the owner unmounts.
 * Callers refresh their own dependent data (candidates, source rows) from `onSettled`, so a
 * finished job never triggers a refetch of the whole Sources list.
 */
export function useCaptureFollow(
  options: {
    onUpdate?: (capture: CorpusCapture) => void;
    onSettled?: (capture: CorpusCapture) => void;
  } = {},
) {
  const capture = ref<CorpusCapture | null>(null);
  const error = ref("");
  let stopFollow: (() => void) | undefined;
  let followedJob = "";
  let stopped = false;

  function clear() {
    stopFollow?.();
    stopFollow = undefined;
    followedJob = "";
  }

  function accept(next: CorpusCapture) {
    const wasActive = Boolean(capture.value?.active_job);
    capture.value = next;
    options.onUpdate?.(next);
    if (next.active_job) follow(next.active_job.id);
    else clear();
    if (!next.active_job && wasActive) options.onSettled?.(next);
  }

  function follow(jobId: string) {
    if (stopped || followedJob === jobId) return;
    clear();
    followedJob = jobId;
    stopFollow = followResource({
      topic: `job:${jobId}`,
      refresh: () => load(),
      isDone: () => !capture.value?.active_job,
    });
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
      // A transient failure keeps following a running job; the next event or fallback read retries.
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
