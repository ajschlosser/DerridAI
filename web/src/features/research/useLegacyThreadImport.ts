/* Copyright 2026 Aaron John Schlosser, PhD. */
import { onBeforeUnmount, ref, watch } from "vue";
import { researchThreadsApi } from "../../api/researchThreads";
import { useAuthStore } from "../../stores/auth";

/** Incremental migration is independent of the authoritative Library reads. */
export function useLegacyThreadImport() {
  const auth = useAuthStore();
  const busy = ref(false);
  const error = ref("");
  const hasMore = ref(true);
  const refreshKey = ref(0);
  let offset = 0;
  let request = 0;
  async function retry() {
    if (busy.value || !auth.can("rag.run")) return;
    const current = ++request;
    busy.value = true;
    error.value = "";
    try {
      const result = await researchThreadsApi.importLegacy(offset);
      if (current !== request) return;
      offset = result.next_offset;
      hasMore.value = result.has_more;
      ++refreshKey.value;
    } catch (reason) {
      if (current === request)
        error.value = reason instanceof Error ? reason.message : String(reason);
    } finally {
      if (current === request) {
        busy.value = false;
        if (hasMore.value && !error.value) void retry();
      }
    }
  }
  watch(
    () => [auth.user?.id, auth.user?.role, auth.can("rag.run")],
    () => {
      ++request;
      offset = 0;
      busy.value = false;
      error.value = "";
      hasMore.value = true;
      if (auth.can("rag.run")) void retry();
    },
    { immediate: true },
  );
  onBeforeUnmount(() => {
    ++request;
  });
  return { busy, error, hasMore, refreshKey, retry };
}
