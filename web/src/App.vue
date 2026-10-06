<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import RouteNavigationFeedback from "./components/shell/RouteNavigationFeedback.vue";
import { createRouteLoading } from "./router/routeLoading";
import { sharedUrlStateCodec, state as sharedState } from "./domain/sharedUrlState";
import { createRuntimeLocationSync } from "./router/runtimeLocationSync";
import { createRuntimeUrlSyncHook } from "./router/runtimeUrlSync";
import { createNavigationHistory, type HistoryEntryTitle } from "./router/navigationHistory";
import { useShellStore, type ShellNavItem } from "./stores/shell";
import { useLayoutStore } from "./stores/workspace";
import { useAuthStore } from "./stores/auth";
import { useI18nStore } from "./stores/i18n";
import AuthScreen from "./components/AuthScreen.vue";
import CommandSearch from "./components/CommandSearch.vue";
import AppNotifications from "./components/AppNotifications.vue";
import MessageDialogHost from "./components/MessageDialogHost.vue";
import RemoveWorkDialog from "./components/RemoveWorkDialog.vue";
import SeparateWorksDialog from "./components/SeparateWorksDialog.vue";
import BulkFieldEditorDialog from "./components/BulkFieldEditorDialog.vue";
import JobDetailsDialog from "./components/JobDetailsDialog.vue";
import JobReviewDialog from "./components/JobReviewDialog.vue";
import LlmTaskLauncherDialog from "./components/LlmTaskLauncherDialog.vue";
import LlmToolResultDialog from "./components/LlmToolResultDialog.vue";
import PdfDraftRecordDialog from "./components/PdfDraftRecordDialog.vue";
import RecordPreviewDialog from "./components/RecordPreviewDialog.vue";
import UpsertQueueDialog from "./components/UpsertQueueDialog.vue";
import RecordFieldEditorDialog from "./components/RecordFieldEditorDialog.vue";
import MergeFilesDialog from "./components/MergeFilesDialog.vue";
import OcrCleanupDialog from "./components/OcrCleanupDialog.vue";
import RecordHistoryDialog from "./components/RecordHistoryDialog.vue";
import WorkMetadataEditorDialog from "./components/WorkMetadataEditorDialog.vue";
import WorkMetadataLlmDialog from "./components/WorkMetadataLlmDialog.vue";
import WorkMetadataProposalDialog from "./components/WorkMetadataProposalDialog.vue";
import MixedWorkValuesDialog from "./components/MixedWorkValuesDialog.vue";
import LlmReviewWorkspace from "./components/LlmReviewWorkspace.vue";
import SemanticMapHost from "./components/semantic/SemanticMapHost.vue";
import SidebarBrand from "./components/shell/SidebarBrand.vue";
import TopbarChrome from "./components/shell/TopbarChrome.vue";
import SidebarNavigator from "./components/shell/SidebarNavigator.vue";
import NavigationCommandPalette from "./components/shell/NavigationCommandPalette.vue";
import SidebarStatus from "./components/shell/SidebarStatus.vue";
import SidebarUtilityNav from "./components/shell/SidebarUtilityNav.vue";
import AppIcon from "./components/AppIcon.vue";
import UiTooltip from "./components/ui/UiTooltip.vue";
import { useMatchMedia } from "./composables/useMatchMedia";
import { useSemanticMapStore } from "./stores/semanticMap";
import type { SidebarNavEntry, SidebarNavGroup } from "./components/shell/sidebarNav";
import {
  CONTEXTUAL_NAV_IDS,
  NAV_SECTION_ORDER,
  NAV_SECTION_TARGETS,
  NAV_TARGETS,
  UTILITY_NAV_IDS,
  navIdForRoute,
} from "./domain/appNavigation";
import { SETTINGS_SECTIONS, resolveSettingsSectionId } from "./domain/settings";
import { viewConfig } from "./domain/runtimeConstants";
import * as runtime from "./domain/appBootstrap";
import { navigateTo, repaintAfterLocationChange } from "./domain/sharedNavigation";
import { viewFromPath } from "./domain/viewPaths";
import { triggerImport } from "./domain/sharedFileLifecycle";
import { pauseRuntime } from "./domain/jobsPause";
import { toggleSidebar } from "./domain/sidebarToggle";
import { CHOOSE_CORPUS_FILES_EVENT } from "./services/corpusFiles";

const router = useRouter();
const route = useRoute();
const navigationHistory = createNavigationHistory(router);
const routeLoading = createRouteLoading(router);
const shell = useShellStore();
const layout = useLayoutStore();
const auth = useAuthStore();
const i18n = useI18nStore();
const semanticMap = useSemanticMapStore();
const runtimeStarted = ref(false);
const handlingAuthExpiry = ref(false);
const topSearch = ref("");
const commandPalette = ref<InstanceType<typeof NavigationCommandPalette> | null>(null);
const corpusFileInput = ref<HTMLInputElement | null>(null);
const mobileNavDialog = ref<HTMLDialogElement | null>(null);
const mobileNavTrigger = ref<HTMLButtonElement | null>(null);
const narrowSidebar = useMatchMedia("(min-width: 781px) and (max-width: 900px)");
const mobileLayout = useMatchMedia("(max-width: 780px)");
const commandShortcut =
  typeof navigator !== "undefined" &&
  /Mac|iPhone|iPad/i.test(navigator.platform || navigator.userAgent || "")
    ? "⌘K"
    : "Ctrl K";
const s = computed(() => shell.snapshot);
const effectiveSidebarCollapsed = computed(() => layout.sidebarCollapsed || narrowSidebar.value);

const pageCapability: Record<string, string> = {
  home: "page.dashboard",
  list: "page.records",
  record: "page.record",
  relationships: "page.record",
  works: "page.works",
  global: "page.search",
  annotations: "page.annotations",
  semanticmap: "page.semantic_map",
  pdf: "page.pdf",
  sources: "page.pdf",
  compare: "page.compare",
  vector: "page.vector",
  rag: "page.research",
  faq: "page.faq",
  responsecache: "page.response_cache",
  systemdata: "page.response_cache",
  metadatamemory: "page.response_cache",
  providers: "page.providers",
  schemas: "page.schemas",
  config: "page.settings",
  users: "page.users",
  languages: "page.languages",
  roles: "page.roles",
  pipelines: "page.response_cache",
};

function canNav(id: string) {
  const capability = pageCapability[id];
  return !capability || auth.can(capability);
}

try {
  const saved = localStorage.getItem("derridai.ui.theme") || "green";
  document.documentElement.dataset.uiTheme = ["green", "blue", "slate"].includes(saved)
    ? saved
    : "green";
  const scheme = localStorage.getItem("derridai.ui.scheme") || "system";
  const contrast = localStorage.getItem("derridai.ui.contrast") || "system";
  const dark =
    scheme === "dark" ||
    (scheme !== "light" && window.matchMedia?.("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.colorScheme = dark ? "dark" : "light";
  if (
    contrast === "more" ||
    (contrast === "system" && window.matchMedia?.("(prefers-contrast: more)").matches)
  )
    document.documentElement.dataset.contrast = "more";
} catch {
  document.documentElement.dataset.uiTheme = "green";
}

function sectionLabel(section: string) {
  const key =
    section === "Corpora"
      ? "section.corpora"
      : section === "Corpus Management"
        ? "section.corpus_management"
        : section === "AI & Automation"
          ? "section.ai_automation"
          : section === "Research"
            ? "section.research"
            : section === "System"
              ? "section.system"
              : "section.overview";
  return i18n.t(key, section);
}

function breadcrumbDestination(path: string): string | undefined {
  return router.resolve(path).path === route.path ? undefined : path;
}

const currentNavId = computed(() =>
  navIdForRoute(route.name, String(route.meta.navId || route.meta.view || s.value.view || "")),
);

function isNavActive(item: { id: string }) {
  return currentNavId.value === item.id;
}

function navEntry(item: ShellNavItem): SidebarNavEntry {
  return {
    id: item.id,
    label:
      item.id === "home"
        ? i18n.t("nav.home")
        : item.id === "responsecache"
          ? i18n.t("runtime.system_data", "System Data")
          : auth.isResearcher && item.id === "vector"
            ? i18n.t("research.corpus_search", item.label)
            : item.label,
    icon: item.icon,
    active: isNavActive(item),
    disabledReason: item.disabledReason,
  };
}

const groupedNavItems = computed<SidebarNavGroup[]>(() => {
  if (!shell.navReady) return [];

  const byId = new Map(
    s.value.nav.filter((item) => canNav(item.id)).map((item) => [item.id, item]),
  );
  const canonical = new Map<string, SidebarNavEntry[]>();
  canonical.set("Overview", []);

  for (const section of NAV_SECTION_ORDER) canonical.set(section, []);

  for (const definition of viewConfig) {
    if (CONTEXTUAL_NAV_IDS.has(definition.id) || UTILITY_NAV_IDS.has(definition.id)) continue;
    const item = byId.get(definition.id);
    if (!item) continue;
    const group = canonical.get(definition.section) || [];
    group.push(navEntry(item));
    canonical.set(definition.section, group);
  }

  if (auth.isAdmin && canNav("sources")) {
    const management = canonical.get("Corpus Management") || [];
    management.unshift({
      id: "sources",
      label: i18n.t("nav.sources"),
      icon: "books",
      active: currentNavId.value === "sources",
    });
    canonical.set("Corpus Management", management);
  }

  if (auth.isAdmin) {
    const automation = canonical.get("AI & Automation") || [];
    const providerIndex = automation.findIndex((item) => item.id === "providers");
    if (canNav("pipelines")) {
      automation.splice(Math.max(0, providerIndex + 1), 0, {
        id: "pipelines",
        label: i18n.t("pipelines.title", "Pipeline Studio"),
        icon: "compare",
        active: currentNavId.value === "pipelines",
      });
    }
    if (canNav("metadatamemory")) {
      automation.push({
        id: "metadatamemory",
        label: i18n.t("nav.metadatamemory"),
        icon: "spark",
        active: currentNavId.value === "metadatamemory",
      });
    }
    canonical.set("AI & Automation", automation);

    const system = canonical.get("System") || [];
    if (canNav("users")) {
      system.push({
        id: "users",
        label: i18n.t("nav.users"),
        icon: "users",
        active: currentNavId.value === "users",
      });
    }
    if (canNav("languages")) {
      system.push({
        id: "languages",
        label: i18n.t("language.manage"),
        icon: "language",
        active: currentNavId.value === "languages",
      });
    }
    canonical.set("System", system);
  }

  return ["Overview", ...NAV_SECTION_ORDER]
    .map((section) => ({
      id: section,
      section: sectionLabel(section),
      items: canonical.get(section) || [],
    }))
    .filter((group) => group.items.length);
});

const utilityNavItems = computed<SidebarNavEntry[]>(() => {
  const items: SidebarNavEntry[] = [];
  if (auth.isAdmin) {
    items.push({
      id: "operations",
      label: i18n.t("ui.operations"),
      icon: "history",
      active: currentNavId.value === "operations",
    });
  }
  items.push({
    id: "help",
    label: i18n.t("help.title", "Help center"),
    icon: "help",
    active: currentNavId.value === "help",
  });
  if (canNav("config")) {
    items.push({
      id: "config",
      label: i18n.t("nav.config"),
      icon: "gear",
      active: currentNavId.value === "config",
    });
  }
  return items;
});

const mobileNavGroups = computed<SidebarNavGroup[]>(() => [
  ...groupedNavItems.value,
  {
    id: "Utilities",
    section: i18n.t("nav.utilities", "Utilities"),
    items: utilityNavItems.value,
  },
]);

function translatedRouteTitle() {
  if (route.name === "record" && s.value.context.title) return s.value.context.title;
  if (route.name === "settings-section") {
    const requested = String(route.params.section || "overview");
    const id = resolveSettingsSectionId(requested) || "overview";
    const section = SETTINGS_SECTIONS.find((item) => item.id === id);
    return section
      ? i18n.t(section.labelKey, section.labelFallback)
      : i18n.t("nav.config", "Settings");
  }
  const key = String(route.meta.titleKey || "");
  const fallback = String(route.meta.titleFallback || s.value.context.title || i18n.t("nav.home"));
  return key ? i18n.t(key, fallback) : fallback;
}

const breadcrumbItems = computed(() => {
  const items: Array<{ label: string; to?: string }> = [];
  const section = String(route.meta.navSection || "");
  if (section && section !== "Overview") {
    const sectionPath =
      NAV_SECTION_TARGETS[section as keyof typeof NAV_SECTION_TARGETS] ||
      NAV_SECTION_TARGETS.System;
    items.push({ label: sectionLabel(section), to: breadcrumbDestination(sectionPath) });
  }

  const parentKey = String(route.meta.breadcrumbParentKey || "");
  if (parentKey) {
    items.push({
      label: i18n.t(parentKey, String(route.meta.breadcrumbParentFallback || "")),
      to: breadcrumbDestination(String(route.meta.breadcrumbParentPath || "/system-data/overview")),
    });
  } else if (route.name === "settings-section") {
    items.push({
      label: i18n.t("nav.config", "Settings"),
      to: breadcrumbDestination("/settings/overview"),
    });
  }

  const title = translatedRouteTitle();
  if (!items.length || items.at(-1)?.label !== title) items.push({ label: title });
  return items;
});

const breadcrumbMeta = computed(() => {
  const name = String(route.name || "");
  if (name === "sources") return i18n.t("sources.help_short");
  if (name === "metadatamemory") return i18n.t("metadata_memory.help");
  if (name === "settings-section") return i18n.t("settings.page_help_short");
  if (name === "list") return i18n.t("context.list.meta");
  if (name === "record") return s.value.context.meta;
  if (name === "relationships") return i18n.t("context.relationships.meta");
  if (name === "global") return i18n.t("context.global.meta");
  if (name === "rag") return i18n.t("context.rag.meta");
  if (name === "faq") return i18n.t("context.faq.meta");
  if (name === "works") return i18n.t("context.works.meta");
  if (name === "annotations") return i18n.t("context.annotations.meta");
  if (name === "semanticmap") return i18n.t("context.semanticmap.meta");
  if (name === "compare") return i18n.t("context.compare.meta");
  if (name === "vector") return i18n.t("context.vector.meta");
  if (name === "corpus-builder" || name === "source-explorer") return i18n.t("context.pdf.meta");
  if (name === "providers") return i18n.t("context.providers.meta");
  if (name === "schemas") return i18n.t("schemas.manage_help");
  if (name === "pipelines") return i18n.t("pipelines.help");
  if (name.startsWith("system-data-")) return i18n.t("runtime.system_data_help");
  if (["users", "roles", "languages", "operations"].includes(name)) return "";
  return "";
});

const canBreadcrumbBack = navigationHistory.canGoBack;
const canBreadcrumbForward = navigationHistory.canGoForward;
function historyLabel(title: HistoryEntryTitle | null, fallbackKey: string) {
  return title && (title.key || title.fallback)
    ? i18n.t(title.key || fallbackKey, title.fallback)
    : i18n.t(fallbackKey);
}
const breadcrumbBackLabel = computed(() =>
  historyLabel(navigationHistory.backTitle.value, "ui.back"),
);
const breadcrumbForwardLabel = computed(() =>
  historyLabel(navigationHistory.forwardTitle.value, "ui.forward"),
);

function onImport(files: FileList) {
  if (auth.isAdmin) triggerImport(files);
}

function onFiles(event: Event) {
  const input = event.target as HTMLInputElement;
  if (input.files?.length) onImport(input.files);
  input.value = "";
}

function openCorpusFilePicker() {
  if (auth.isAdmin) corpusFileInput.value?.click();
}

function syncSharedStateFromRoute() {
  sharedUrlStateCodec.applyUrlState();
  repaintAfterLocationChange();
}

function navigateNative(path: string) {
  const current = router.currentRoute.value.fullPath;
  const target = router.resolve(path).fullPath;
  if (current === target) {
    // The router remains authoritative even if compatibility state drifted.
    // Re-derive that state from the settled URL instead of initiating a second
    // forward-navigation path through sharedNavigation.navigateTo().
    const expectedView = viewFromPath(router.currentRoute.value.path);
    if (expectedView && sharedState.view !== expectedView) syncSharedStateFromRoute();
    return;
  }
  void router.push(target).catch(() => {
    // The route feedback panel exposes the failure and recovery actions.
  });
}

function navigate(view: string) {
  const target = NAV_TARGETS[view];
  if (!target) return;
  navigateNative(target.path);
}

function openMobileNavigation() {
  if (!mobileLayout.value) return;
  if (mobileNavDialog.value && !mobileNavDialog.value.open) mobileNavDialog.value.showModal();
}

function closeMobileNavigation() {
  mobileNavDialog.value?.close();
  window.setTimeout(() => mobileNavTrigger.value?.focus(), 0);
}

function navigateFromMobile(view: string) {
  mobileNavDialog.value?.close();
  navigate(view);
}

function goBreadcrumbBack() {
  navigationHistory.back();
}

function goBreadcrumbForward() {
  navigationHistory.forward();
}

function searchCorpus(query: string) {
  const value = query.trim();
  if (!value) return;
  topSearch.value = value;
  sharedState.globalSearch = value;
  sharedState.storeQuery = value;
  sharedState.globalPage = 1;
  sharedState.storeSearchResults = [];
  sharedState.globalSearchMode = "traditional";
  navigateTo("global");
}

function submitTopSearch() {
  searchCorpus(topSearch.value);
}

async function startRuntime() {
  if (!auth.user || runtimeStarted.value) return;
  runtimeStarted.value = true;
  runtime.setUserContext(auth.user);
  runtime.setShellRefreshHook(() => shell.sync());
  shell.syncNav();
  runtime.setUrlSyncHook(createRuntimeUrlSyncHook(router, () => runtime.syncFromLocation()));
  try {
    const requiredCapability = String(route.meta.capability || "");
    if (requiredCapability && !auth.can(requiredCapability)) await router.replace("/");
    if (!i18n.languages.length) await i18n.initialize();
    await runtime.bootstrapRuntime();
    shell.sync();
    shell.ready = true;
  } catch (error) {
    runtimeStarted.value = false;
    console.error("DerridAI runtime bootstrap failed", error);
    throw error;
  }
}

async function logout() {
  pauseRuntime();
  runtimeStarted.value = false;
  await auth.logout();
  await router.replace("/");
}

async function handleAuthExpired() {
  if (handlingAuthExpiry.value || !auth.user) return;
  handlingAuthExpiry.value = true;
  try {
    pauseRuntime();
    runtimeStarted.value = false;
    auth.expireSession(i18n.t("auth.session_expired"));
    if (router.currentRoute.value.path !== "/") await router.replace("/");
  } finally {
    queueMicrotask(() => {
      handlingAuthExpiry.value = false;
    });
  }
}

onMounted(async () => {
  window.addEventListener(CHOOSE_CORPUS_FILES_EVENT, openCorpusFilePicker);
  window.addEventListener("derridai-auth-expired", () => {
    void handleAuthExpired();
  });
  window.addEventListener("derridai:permissions-changed", () => {
    void auth.loadStatus();
  });
  window.addEventListener("derridai:navigate-native", ((event: Event) => {
    const detail = (event as CustomEvent<{ path?: string }>).detail || {};
    if (detail.path) navigateNative(detail.path);
  }) as EventListener);
  window.addEventListener("keydown", (event: KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      commandPalette.value?.open();
    }
  });
  if (!auth.initialized) await auth.loadStatus();
  if (!i18n.languages.length) await i18n.initialize();
  await startRuntime();
});

onBeforeUnmount(() => {
  runtimeLocationSync.dispose();
  navigationHistory.dispose();
  routeLoading.dispose();
  window.removeEventListener(CHOOSE_CORPUS_FILES_EVENT, openCorpusFilePicker);
});

// The router is the authority on where the user is. When navigation settles on a
// different compatibility view, or comes from browser Back/Forward, derive the
// shared workspace state from that settled URL rather than initiating navigation
// from the compatibility layer.
const runtimeLocationSync = createRuntimeLocationSync(router, {
  isStarted: () => runtimeStarted.value,
  viewForPath: (path) => viewFromPath(path),
  currentView: () => sharedState.view,
  sync: syncSharedStateFromRoute,
});

watch(
  () => auth.user?.id,
  (id) => {
    if (!id) {
      pauseRuntime();
      runtimeStarted.value = false;
      shell.resetNav();
      return;
    }
    void startRuntime();
  },
);
</script>

<template>
  <div v-if="!auth.initialized" class="auth-loading">{{ i18n.t("ui.loading_derridai") }}</div>
  <AuthScreen v-else-if="!auth.user" />
  <div
    v-else
    class="app-shell app-shell-modern"
    :class="{ 'sidebar-collapsed': effectiveSidebarCollapsed }"
  >
    <a class="skip-link" href="#appContent">{{ i18n.t("ui.skip_to_content") }}</a>
    <aside class="sidebar shell-sidebar">
      <SidebarBrand
        :collapsed="effectiveSidebarCollapsed"
        @navigate-home="navigate('home')"
        @toggle="toggleSidebar()"
      />
      <SidebarNavigator
        :groups="groupedNavItems"
        :collapsed="effectiveSidebarCollapsed"
        @navigate="navigate"
      />
      <SidebarUtilityNav
        :items="utilityNavItems"
        :collapsed="effectiveSidebarCollapsed"
        @navigate="navigate"
      />
      <SidebarStatus
        v-if="!effectiveSidebarCollapsed"
        :is-admin="auth.isAdmin"
        :has-corpus-db="s.hasCorpusDb"
        :total-loaded="s.totalLoaded"
        :corpus-store-count="s.corpusStoreCount"
        :active-store="s.activeStore"
        :db-records="s.dbRecords"
        :selected-evidence-count="s.selectedEvidenceCount"
      />
    </aside>

    <section class="workspace shell-workspace">
      <header class="topbar shell-topbar">
        <UiTooltip
          :text="i18n.t('nav.open_navigation')"
          trigger-mode="content"
          :content-focusable="false"
          placement="bottom"
        >
          <button
            ref="mobileNavTrigger"
            class="mobile-navigation-trigger"
            type="button"
            :aria-label="i18n.t('nav.open_navigation')"
            @click="openMobileNavigation"
          >
            <AppIcon name="list" aria-hidden="true" />
          </button>
        </UiTooltip>
        <CommandSearch
          v-model="topSearch"
          shortcut=""
          :placeholder="i18n.t('ui.global_search_placeholder')"
          @submit="submitTopSearch"
        />
        <div class="shell-top-actions">
          <UiTooltip
            :text="i18n.t('nav.command_palette')"
            trigger-mode="content"
            :content-focusable="false"
            placement="bottom"
          >
            <button
              class="shell-command-palette-button"
              type="button"
              :aria-label="i18n.t('nav.command_palette')"
              @click="commandPalette?.open()"
            >
              {{ i18n.t("nav.command_palette") }} <kbd>{{ commandShortcut }}</kbd>
            </button>
          </UiTooltip>
          <input
            ref="corpusFileInput"
            id="fileInput"
            type="file"
            accept=".jsonl,.ndjson,.json,.zst"
            multiple
            hidden
            @change="onFiles"
          />
          <TopbarChrome
            :is-admin="auth.isAdmin"
            :can-faq="auth.can('page.faq')"
            :can-settings="auth.can('page.settings')"
            :username="auth.user.username"
            :role="auth.user.role"
            :role-name="auth.user.role_name"
            :languages="i18n.languages"
            :locale="i18n.locale"
            :locale-loading="i18n.loading"
            @navigate="navigate"
            @logout="logout"
            @locale="i18n.setLocale($event)"
          />
        </div>
      </header>
      <nav class="vue-breadcrumb shell-breadcrumb" :aria-label="i18n.t('ui.navigation_history')">
        <div class="breadcrumb-nav">
          <UiTooltip
            :text="breadcrumbBackLabel"
            trigger-mode="content"
            :content-focusable="!canBreadcrumbBack"
            placement="bottom"
          >
            <button
              class="breadcrumb-nav-button"
              type="button"
              :disabled="!canBreadcrumbBack"
              :aria-label="i18n.t('ui.back')"
              @click="goBreadcrumbBack"
            >
              <span aria-hidden="true">←</span>
              <span class="breadcrumb-button-label">{{ i18n.t("ui.back") }}</span>
            </button>
          </UiTooltip>
          <UiTooltip
            :text="breadcrumbForwardLabel"
            trigger-mode="content"
            :content-focusable="!canBreadcrumbForward"
            placement="bottom"
          >
            <button
              class="breadcrumb-nav-button"
              type="button"
              :disabled="!canBreadcrumbForward"
              :aria-label="i18n.t('ui.forward')"
              @click="goBreadcrumbForward"
            >
              <span class="breadcrumb-button-label">{{ i18n.t("ui.forward") }}</span>
              <span aria-hidden="true">→</span>
            </button>
          </UiTooltip>
        </div>
        <div class="vue-breadcrumb-path">
          <RouterLink to="/">DerridAI</RouterLink>
          <template v-for="(item, index) in breadcrumbItems" :key="`${item.label}-${index}`">
            <b aria-hidden="true">›</b>
            <RouterLink v-if="item.to && index < breadcrumbItems.length - 1" :to="item.to">
              {{ item.label }}
            </RouterLink>
            <strong v-else>{{ item.label }}</strong>
          </template>
          <span v-if="breadcrumbMeta" class="shell-breadcrumb-meta">{{ breadcrumbMeta }}</span>
        </div>
      </nav>
      <div
        class="shell-body"
        :class="{
          'with-semantic-map':
            semanticMap.enabled &&
            semanticMap.placement === 'sidebar' &&
            route.name !== 'semanticmap',
        }"
      >
        <div id="appContent" class="app-content-region" tabindex="-1">
          <RouterView />
          <Teleport to="body">
            <RouteNavigationFeedback
              v-if="routeLoading.visible.value || routeLoading.failed.value"
              :destination="
                i18n.t(
                  String(
                    (routeLoading.failed.value || routeLoading.destination.value)?.meta.titleKey ||
                      'ui.loading',
                  ),
                  String(
                    (routeLoading.failed.value || routeLoading.destination.value)?.meta
                      .titleFallback || '',
                  ),
                )
              "
              :failed="Boolean(routeLoading.failed.value)"
              @retry="routeLoading.retry"
              @reload="routeLoading.reload"
            />
          </Teleport>
        </div>
        <SemanticMapHost />
      </div>
    </section>
  </div>
  <dialog
    ref="mobileNavDialog"
    class="mobile-navigation-drawer"
    :aria-label="i18n.t('ui.primary_navigation')"
    @cancel.prevent="closeMobileNavigation"
  >
    <header class="mobile-navigation-header">
      <div>
        <strong>DerridAI</strong>
        <span>{{ i18n.t("ui.primary_navigation") }}</span>
      </div>
      <button
        type="button"
        class="mobile-navigation-close"
        :aria-label="i18n.t('nav.close_navigation')"
        @click="closeMobileNavigation"
      >
        <AppIcon name="close" aria-hidden="true" />
      </button>
    </header>
    <SidebarNavigator :groups="mobileNavGroups" :collapsed="false" @navigate="navigateFromMobile" />
  </dialog>
  <NavigationCommandPalette
    ref="commandPalette"
    :groups="mobileNavGroups"
    @navigate="navigate"
    @search="searchCorpus"
  />
  <LlmReviewWorkspace />
  <AppNotifications />
  <MessageDialogHost />
  <MixedWorkValuesDialog />
  <RemoveWorkDialog />
  <MergeFilesDialog />
  <BulkFieldEditorDialog />
  <OcrCleanupDialog />
  <RecordHistoryDialog />
  <RecordFieldEditorDialog />
  <UpsertQueueDialog />
  <RecordPreviewDialog />
  <JobDetailsDialog />
  <JobReviewDialog />
  <LlmToolResultDialog />
  <LlmTaskLauncherDialog />
  <PdfDraftRecordDialog />
  <WorkMetadataEditorDialog />
  <WorkMetadataLlmDialog />
  <WorkMetadataProposalDialog />
  <SeparateWorksDialog />
</template>

<style scoped>
.shell-body {
  display: flex;
  flex: 1;
  min-height: 0;
  min-width: 0;
}
.shell-body .app-content-region {
  flex: 1;
  min-width: 0;
}
.vue-breadcrumb {
  display: flex;
  align-items: center;
  gap: 10px;
}
.auth-loading {
  min-height: 100vh;
  display: grid;
  place-items: center;
  color: var(--muted);
  font-size: 0.875rem;
  background: var(--bg);
}
.app-shell-modern {
  --ref-sidebar: 252px;
  grid-template-columns: var(--ref-sidebar) minmax(0, 1fr);
  min-height: 100vh;
  background: var(--ref-bg);
}
.shell-sidebar {
  padding: 12px 11px 10px;
}
.shell-workspace {
  min-width: 0;
  background: linear-gradient(180deg, var(--card) 0, var(--card) 100%);
}
.shell-top-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.mobile-navigation-trigger {
  display: none;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--card);
  color: var(--text);
  cursor: pointer;
}
.mobile-navigation-trigger :deep(svg) {
  width: 19px;
  height: 19px;
}
.mobile-navigation-drawer {
  width: min(360px, calc(100vw - 28px));
  height: calc(100dvh - 20px);
  max-height: none;
  margin: 10px auto 10px 10px;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
  color: var(--text);
  box-shadow: 0 24px 80px color-mix(in srgb, var(--text) 24%, transparent);
}

.mobile-navigation-drawer::backdrop {
  background: color-mix(in srgb, var(--text) 38%, transparent);
}
.mobile-navigation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 14px 10px;
  border-bottom: 1px solid var(--line);
}
.mobile-navigation-header > div {
  display: grid;
  gap: 2px;
}
.mobile-navigation-header strong {
  font-size: 0.9375rem;
}
.mobile-navigation-header span {
  color: var(--muted);
  font-size: 0.75rem;
}
.mobile-navigation-close {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: transparent;
  color: inherit;
  cursor: pointer;
}
.mobile-navigation-close :deep(svg) {
  width: 18px;
  height: 18px;
}
.mobile-navigation-drawer :deep(.shell-navigation) {
  max-height: calc(100dvh - 92px);
  padding: 12px;
}
.shell-command-palette-button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 32px;
  padding: 5px 8px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--card);
  color: var(--muted);
  font: inherit;
  font-size: 0.75rem;
  font-weight: 650;
  cursor: pointer;
}
.shell-command-palette-button:hover,
.shell-command-palette-button:focus-visible {
  color: var(--text);
  background: var(--soft);
}
.shell-command-palette-button kbd {
  font-size: 0.75rem;
  font-weight: 700;
}
.vue-breadcrumb-path a {
  color: var(--muted);
  text-decoration: none;
}
.vue-breadcrumb-path a:hover,
.vue-breadcrumb-path a:focus-visible {
  color: var(--text);
  text-decoration: underline;
}
.shell-breadcrumb-meta {
  margin-left: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.skip-link {
  position: fixed;
  left: 12px;
  top: 8px;
  z-index: 2000;
  padding: 9px 12px;
  border-radius: 7px;
  background: var(--tone-info-fg);
  color: var(--accent-on);
  font-size: 0.8125rem;
  font-weight: 700;
  transform: translateY(-150%);
}
.skip-link:focus {
  transform: translateY(0);
  outline: 3px solid var(--card) !important;
  box-shadow: 0 0 0 5px var(--ui-accent);
}
@media (prefers-reduced-motion: reduce) {
  .skip-link {
    transition: none;
  }
}
@media (max-width: 1100px) {
  .shell-command-palette-button {
    width: 34px;
    overflow: hidden;
    white-space: nowrap;
  }
  .shell-command-palette-button kbd {
    display: none;
  }
}
@media (max-width: 1250px) and (min-width: 901px) {
  .app-shell-modern {
    --ref-sidebar: 228px;
  }
}
@media (max-width: 900px) {
  .app-shell-modern {
    grid-template-columns: 64px minmax(0, 1fr);
  }
  .shell-sidebar {
    padding: 9px 7px;
  }
}
@media (max-width: 780px) {
  .app-shell-modern {
    display: block;
  }
  .shell-sidebar {
    display: none;
  }
  .mobile-navigation-trigger {
    display: grid;
  }
  .shell-topbar {
    gap: 8px;
  }
}
@media (max-width: 650px) {
  .shell-top-actions {
    display: flex;
    flex: 0 0 auto;
    gap: 4px;
  }
  .shell-command-palette-button {
    display: none;
  }
  .app-content-region {
    padding-bottom: 64px;
  }
}
</style>
