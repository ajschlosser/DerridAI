// Copyright 2026 Aaron John Schlosser, PhD.
import { ref } from "vue";
import * as runtime from "../runtime/runtime.js";
import type { AnnotationWorkspaceItem, AnnotationsWorkspaceSnapshot } from "../types/annotations";

export function useAnnotationsWorkspace() {
  const snapshot = ref<AnnotationsWorkspaceSnapshot | null>(null);
  const loading = ref(false);
  const error = ref("");
  const removing = ref<string | null>(null);
  let queryTimer: number | undefined;

  async function load(force = false) {
    loading.value = true;
    error.value = "";
    try {
      snapshot.value = (await runtime.loadAnnotationsWorkspace(
        force || Boolean(snapshot.value),
      )) as AnnotationsWorkspaceSnapshot;
    } catch (exception) {
      error.value = exception instanceof Error ? exception.message : String(exception);
    } finally {
      loading.value = false;
    }
  }

  function setQuery(value: string) {
    runtime.setAnnotationsWorkspaceQuery(value);
    if (snapshot.value) snapshot.value = { ...snapshot.value, query: value };
    window.clearTimeout(queryTimer);
    queryTimer = window.setTimeout(() => void load(), 150);
  }

  function setView(view: "works" | "recent") {
    runtime.setAnnotationsWorkspaceView(view);
    if (snapshot.value) snapshot.value = { ...snapshot.value, view };
  }

  function openRecord(annotation: AnnotationWorkspaceItem) {
    runtime.openAnnotationsWorkspaceRecord(annotation);
  }

  function openWork(work: string) {
    runtime.openAnnotationsWorkspaceWork(work);
  }

  async function remove(annotation: AnnotationWorkspaceItem) {
    if (!annotation.removable || removing.value) return false;
    removing.value = annotation.id;
    try {
      await runtime.removeAnnotationsWorkspaceItem(annotation);
      await load(true);
      return true;
    } catch (exception) {
      runtime.notifyToast(exception instanceof Error ? exception.message : String(exception), {
        tone: "danger",
      });
      return false;
    } finally {
      removing.value = null;
    }
  }

  return {
    snapshot,
    loading,
    error,
    removing,
    load,
    setQuery,
    setView,
    openRecord,
    openWork,
    remove,
  };
}
