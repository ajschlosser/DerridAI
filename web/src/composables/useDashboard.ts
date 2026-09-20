// Copyright 2026 Aaron John Schlosser, PhD.
import { ref } from "vue";
import { useRouter } from "vue-router";
import { chromaApi } from "../api/chroma";
import type { DashboardSearchMode, DashboardSnapshot } from "../types/dashboard";

export function useDashboard() {
  const router = useRouter();
  const snapshot = ref<DashboardSnapshot | null>(null);
  const loading = ref(true);
  const error = ref("");
  async function refresh() {
    loading.value = true;
    error.value = "";
    try {
      const stores = await chromaApi.collections();
      const activeStore = stores.find((store) => store.collection_role !== "system") ?? null;
      const response = activeStore ? await chromaApi.works(activeStore.name) : { stats: [] };
      const works = response.stats
        .map((item) => ({ work: item.work, count: Number(item.count || 0), year: "" }))
        .sort((left, right) => left.work.localeCompare(right.work));
      snapshot.value = {
        totals: {
          records: activeStore?.count || 0,
          works: works.length,
          changes: 0,
          dbs: stores.filter((store) => store.collection_role !== "system").length,
        },
        works,
        query: "",
        mode: "traditional",
        activeStore: activeStore?.name || null,
      };
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : String(exc);
    } finally {
      loading.value = false;
    }
  }
  function search(query: string, work: string, mode: DashboardSearchMode) {
    void router.push({
      path: "/search",
      query: { q: query || undefined, work: work || undefined, mode },
    });
  }
  return {
    snapshot,
    loading,
    error,
    refresh,
    search,
    openView: (view: "works" | "list" | "vector") => void router.push({ name: view }),
    searchWork: (work: string) => search("", work, "traditional"),
  };
}
