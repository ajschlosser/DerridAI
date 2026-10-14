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

import { shallowReadonly, shallowRef } from "vue";

export type OcrCleanupScope = "active" | "selected" | "review" | "all";

export interface OcrCleanupRequest {
  /** The active tab, or null when no tab is open (its scope is then disabled). */
  active: { name: string; recordCount: number } | null;
  selectedCount: number;
  reviewCount: number;
  allCount: number;
  fileCount: number;
  /** Runs after the dialog has closed: resolves the scope to rows, confirms and cleans them. */
  choose: (scope: OcrCleanupScope) => Promise<void>;
}

const current = shallowRef<OcrCleanupRequest | null>(null);

/** Choose which records the OCR artifact cleanup runs over. */
export function openOcrCleanupDialog(request: OcrCleanupRequest) {
  current.value = request;
}

export function closeOcrCleanupDialog() {
  current.value = null;
}

export function useOcrCleanupDialog() {
  return { current: shallowReadonly(current), close: closeOcrCleanupDialog };
}
