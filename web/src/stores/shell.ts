import { computed, ref } from "vue";
import { defineStore } from "pinia";
import * as runtime from "../runtime/runtime.js";

export interface ShellFile {
  id: string;
  name: string;
  count: number;
  dirty: number;
  active: boolean;
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
  sidebarCollapsed: boolean;
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
  canGoBack: boolean;
  canGoForward: boolean;
  backLabel: string;
  forwardLabel: string;
  selectedEvidenceCount: number;
  systemHtml: string;
  nav: ShellNavItem[];
}

const emptySnapshot: ShellSnapshot = {
  view: "home",
  sidebarCollapsed: false,
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
  canGoBack: false,
  canGoForward: false,
  backLabel: "",
  forwardLabel: "",
  selectedEvidenceCount: 0,
  systemHtml: "",
  nav: [],
};

export const useShellStore = defineStore("shell", () => {
  const snapshot = ref<ShellSnapshot>(emptySnapshot);
  const ready = ref(false);

  function sync() {
    snapshot.value = runtime.getShellSnapshot() as ShellSnapshot;
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

  return { snapshot, ready, groupedNav, sync };
});
