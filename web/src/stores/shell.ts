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

import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { getNavItems } from "../domain/navItems";
import { getShellSnapshot } from "../domain/shellSnapshot";

export interface ShellFile {
  id: string;
  name: string;
  count: number;
  dirty: number;
  active: boolean;
  origin?: string;
  origin_detail?: string;
}
export interface ShellNavItem {
  id: string;
  label: string;
  icon: string;
  section: string;
  disabledReason?: string;
}
export interface ShellSnapshot {
  view: string;
  files: ShellFile[];
  context: { kicker: string; title: string; meta: string };
  totalLoaded: number;
  flagged: number;
  pending: number;
  activeJobs: number;
  corpusStoreCount: number;
  dbRecords: number;
  cacheCount: number;
  hasCorpusDb: boolean;
  dbUnavailableReason: string;
  activeStore: string;
  canEdit: boolean;
  selectedEvidenceCount: number;
  systemHtml: string;
  nav: ShellNavItem[];
}

const emptySnapshot: ShellSnapshot = {
  view: "home",
  files: [],
  context: { kicker: "Overview", title: "Dashboard", meta: "" },
  totalLoaded: 0,
  flagged: 0,
  pending: 0,
  activeJobs: 0,
  corpusStoreCount: 0,
  dbRecords: 0,
  cacheCount: 0,
  hasCorpusDb: false,
  dbUnavailableReason: "",
  activeStore: "",
  canEdit: false,
  selectedEvidenceCount: 0,
  systemHtml: "",
  nav: [],
};

export const useShellStore = defineStore("shell", () => {
  const snapshot = ref<ShellSnapshot>(emptySnapshot);
  const ready = ref(false);

  // True once the navigation list has been computed for the signed-in user. The shell
  // must not draw a partial menu (only the Vue-side admin items) before this.
  const navReady = ref(false);

  function sync() {
    snapshot.value = getShellSnapshot() as ShellSnapshot;
    navReady.value = true;
  }

  // Publish only the menu. Cheap and independent of workspace bootstrap, so it can run
  // the moment a user signs in instead of waiting for the first full snapshot.
  function syncNav() {
    snapshot.value = { ...snapshot.value, nav: getNavItems() as ShellNavItem[] };
    navReady.value = true;
  }

  function resetNav() {
    snapshot.value = { ...snapshot.value, nav: [] };
    navReady.value = false;
  }

  const groupedNav = computed(() => {
    const groups: Array<{ section: string; items: ShellNavItem[] }> = [];
    for (const item of snapshot.value.nav) {
      let group = groups.at(-1);
      if (!group || group.section !== item.section) {
        group = { section: item.section, items: [] };
        groups.push(group);
      }
      group.items.push(item);
    }
    return groups;
  });

  return { snapshot, ready, navReady, groupedNav, sync, syncNav, resetNav };
});
