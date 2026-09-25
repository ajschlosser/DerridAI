// Copyright 2026 Aaron John Schlosser, PhD.
import { ref } from "vue";
import { annotationsService } from "../services/annotations";
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
      snapshot.value = await annotationsService.loadWorkspace(force || Boolean(snapshot.value));
    } catch (exception) {
      error.value = exception instanceof Error ? exception.message : String(exception);
    } finally {
      loading.value = false;
    }
  }

  function setQuery(value: string) {
    annotationsService.setQuery(value);
    if (snapshot.value) snapshot.value = { ...snapshot.value, query: value };
    window.clearTimeout(queryTimer);
    queryTimer = window.setTimeout(() => void load(), 150);
  }

  function setView(view: "works" | "recent") {
    annotationsService.setView(view);
    if (snapshot.value) snapshot.value = { ...snapshot.value, view };
  }

  function openRecord(annotation: AnnotationWorkspaceItem) {
    annotationsService.openRecord(annotation);
  }

  function openWork(work: string) {
    annotationsService.openWork(work);
  }

  async function remove(annotation: AnnotationWorkspaceItem) {
    if (!annotation.removable || removing.value) return false;
    removing.value = annotation.id;
    try {
      await annotationsService.removeWorkspaceItem(annotation);
      await load(true);
      return true;
    } catch (exception) {
      window.dispatchEvent(
        new CustomEvent("derridai:toast", {
          detail: {
            message: exception instanceof Error ? exception.message : String(exception),
            tone: "danger",
          },
        }),
      );
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
