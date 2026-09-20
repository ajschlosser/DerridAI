// Copyright 2026 Aaron John Schlosser, PhD.
import { computed, ref } from "vue";
import { annotationsApi } from "../api/annotations";
import type { Annotation, AnnotationDraft } from "../types/annotations";

const shared = ref<Annotation[]>([]);
const loadedStore = ref("");
const loading = ref(false);

function key(annotation: Annotation) {
  return String(annotation.shared_annotation_id || annotation.id);
}

function dedupe(items: Annotation[]) {
  const seen = new Set<string>();
  return items.filter((item) => {
    const id = key(item);
    if (seen.has(id)) return false;
    seen.add(id);
    return true;
  });
}

export function useAnnotations() {
  const annotations = computed(() => shared.value);
  async function load(store?: string) {
    loading.value = true;
    try {
      const response = await annotationsApi.list(store);
      shared.value = dedupe(response.annotations || []);
      loadedStore.value = store || "";
      return shared.value;
    } finally {
      loading.value = false;
    }
  }
  async function create(payload: AnnotationDraft) {
    const created = await annotationsApi.create(payload);
    shared.value = dedupe([created, ...shared.value]);
    return created;
  }
  async function remove(id: string) {
    await annotationsApi.remove(id);
    shared.value = shared.value.filter((item) => key(item) !== id && item.id !== id);
  }
  function forRecord(recordId: string, store?: string) {
    return shared.value.filter(
      (item) => item.record_id === recordId && (!store || item.store === store),
    );
  }
  return { annotations, loadedStore, loading, load, create, remove, forRecord };
}
