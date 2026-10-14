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

import { reviewKey } from "./evidenceSelection";
import { selectedRecord } from "./sharedRecordScopes";
import { activeFile, selectedIndex } from "./sharedUrlState";
import {
  publishTouchupWorkspaceRequest,
  type TouchupWorkspaceItem,
} from "../features/touchup/touchupWorkspaceRequest";

// Opens the feature-owned touch-up workspace request over the given review items,
// or over the selected record when none are given. The historical window event is
// still emitted as a compatibility notification, but it is no longer responsible
// for delivering the request to the Vue workspace.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

export function normalizeTouchupItems(inputItems: Any[] | null = null): Any[] {
  const fallback = (() => {
    const file = activeFile(),
      record = selectedRecord();
    if (!file || !record) return [];
    const index = selectedIndex(file);
    return [{ file, index, record, key: reviewKey(file, index) }];
  })();
  return (inputItems?.length ? inputItems : fallback)
    .map((item: Any) => ({
      ...item,
      record: item.file.records[item.index],
      key: item.key || reviewKey(item.file, item.index),
    }))
    .filter((item: Any) => item.record);
}

export function openTouchup(inputItems: Any[] | null = null, initialMode = "foreground"): void {
  const items = normalizeTouchupItems(inputItems);
  if (!items.length) return;
  const request = { items: items as TouchupWorkspaceItem[], initialMode };
  publishTouchupWorkspaceRequest(request);
  window.dispatchEvent(new CustomEvent("derridai:open-touchup", { detail: request }));
}
