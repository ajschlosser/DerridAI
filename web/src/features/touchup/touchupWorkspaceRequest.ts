/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 */

import { shallowReadonly, shallowRef } from "vue";

export type TouchupRecord = Record<string, unknown>;

export interface TouchupWorkspaceItem {
  file: { name?: string; records: TouchupRecord[] };
  index: number;
  record: TouchupRecord;
  key: string;
}

export interface TouchupWorkspaceRequest {
  items: TouchupWorkspaceItem[];
  initialMode: string;
}

const current = shallowRef<TouchupWorkspaceRequest | null>(null);

/**
 * Feature-owned command state for opening the LLM touch-up workspace.
 *
 * This replaces the window event as the authoritative delivery mechanism so
 * the workspace implementation can be lazy-loaded without losing an open
 * request while its JavaScript chunk is still loading.
 */
export function publishTouchupWorkspaceRequest(request: TouchupWorkspaceRequest): void {
  current.value = request;
}

export function clearTouchupWorkspaceRequest(): void {
  current.value = null;
}

export function useTouchupWorkspaceRequest() {
  return {
    current: shallowReadonly(current),
    clear: clearTouchupWorkspaceRequest,
  };
}
