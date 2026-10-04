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

import { state } from "./sharedUrlState";
import { isResearcher } from "./sharedSession";
import { navigateTo, renderView, syncUrl } from "./sharedNavigation";
import { persistPrefs, shell } from "./sharedWorkspaceStorage";

// The corpus-workspace actions Vue views call: open a file in Records, and jump to Search from a metadata value.

export function searchByMetadata(
  field: string,
  value: unknown,
  { contains = false }: { contains?: boolean } = {},
) {
  const raw = String(value ?? "").trim();
  if (!field || !raw) return;
  state.globalPage = 1;
  state.storeSearchResults = [];
  if (isResearcher()) {
    state.globalSearchMode = "database";
    state.dbSearchMethod = "filter";
    state.dbSearchWhere = { [field]: contains ? { $contains: raw } : raw };
    state.globalSearch = "";
    state.globalSearchAutoRun = true;
  } else {
    state.globalSearchMode = "traditional";
    state.globalSearch = "";
    state.globalFilters = [
      { id: crypto.randomUUID(), field, op: contains ? "has" : "eq", value: raw },
    ];
  }
  persistPrefs();
  navigateTo("global");
}

export function activateFile(fileId: string) {
  if (["list", "record"].includes(state.view)) {
    state.activeFileId = fileId;
    persistPrefs();
    syncUrl({ replace: true });
    shell();
    renderView();
  } else navigateTo("list", { fileId });
}
