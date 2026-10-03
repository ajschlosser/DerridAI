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
