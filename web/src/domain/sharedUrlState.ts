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

import { bindWorkspaceGroups } from "../state/workspaceState";
import { createUrlStateCodec } from "./urlStateCodec";

// The URL codec over the shared workspace state, usable without the legacy runtime. The runtime's state object reads
// the same shared groups, so reading and applying a URL here and there is the same operation.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

export const state = bindWorkspaceGroups({}) as Loose;

export const activeFile = () => state.files.find((f: Loose) => f.id === state.activeFileId) || null;
export const selectedIndex = (f: Loose | null) =>
  Math.max(0, Math.min((f?.records.length || 1) - 1, state.selected[f?.id] ?? 0));
export const dbSearchWhere = () =>
  Object.fromEntries(
    Object.entries(state.dbSearchWhere || {}).filter(
      ([, value]) => String(value ?? "").trim() !== "",
    ),
  );

export const sharedUrlStateCodec = createUrlStateCodec({
  state,
  activeFile,
  dbSearchWhere,
  selectedIndex,
});
