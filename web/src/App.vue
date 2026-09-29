<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import { useShellStore, type ShellNavItem } from "./stores/shell";
import { useAuthStore } from "./stores/auth";
import { useI18nStore } from "./stores/i18n";
import AuthScreen from "./components/AuthScreen.vue";
import CommandSearch from "./components/CommandSearch.vue";
import AppNotifications from "./components/AppNotifications.vue";
import LlmReviewWorkspace from "./components/LlmReviewWorkspace.vue";
import SidebarBrand from "./components/shell/SidebarBrand.vue";
import TopbarChrome from "./components/shell/TopbarChrome.vue";
import SidebarNavigator from "./components/shell/SidebarNavigator.vue";
import NavigationCommandPalette from "./components/shell/NavigationCommandPalette.vue";
import SidebarStatus from "./components/shell/SidebarStatus.vue";
import type { SidebarNavEntry, SidebarNavGroup } from "./components/shell/sidebarNav";
import {
  CONTEXTUAL_NAV_IDS,
  NAV_SECTION_ORDER,
  NAV_TARGETS,
  navIdForRoute,
} from "./domain/appNavigation";
import { SETTINGS_SECTIONS, isSettingsSectionId } from "./domain/settings";
import { viewConfig } from "./domain/runtimeConstants";
import * as runtime from "./runtime/runtime.js";

const router = useRouter();
const route = useRoute();
const shell = useShellStore();
const auth = useAuthStore();
const i18n = useI18nStore();
const runtimeStarted = ref(false);
const handlingAuthExpiry = ref(false);
const topSearch = ref("");
const commandPalette = ref<InstanceType<typeof NavigationCommandPalette> | null>(null);
const commandShortcut =
  typeof navigator !== "undefined" &&
  /Mac|iPhone|iPad/i.test(navigator.platform || navigator.userAgent || "")
    ? "⌘K"
    : "Ctrl K";
const nativeBackPath = ref<string | null>(null);
const nativeForwardPath = ref<string | null>(null);
const s = computed(() => shell.snapshot);

const pageCapability: Record<string, string> = {
  home: "page.dashboard",
  list: "page.records",
  record: "page.record",
  relationships: "page.record",
  works: "page.works",
  global: "page.search",
  annotations: "page.annotations",
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
      : section === "Build"
        ? "section.build"
        : section === "Research"
          ? "section.research"
          : section === "System"
            ? "section.system"
            : "section.overview";
  return i18n.t(key, section);
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

  const byId = new Map(s.value.nav.filter((item) => canNav(item.id)).map((item) => [item.id, item]));
  const canonical = new Map<string, SidebarNavEntry[]>();
  canonical.set("Overview", []);

  for (const section of NAV_SECTION_ORDER) canonical.set(section, []);

  for (const definition of viewConfig) {
    if (CONTEXTUAL_NAV_IDS.has(definition.id)) continue;
    const item = byId.get(definition.id);
    if (!item) continue;
    const group = canonical.get(definition.section) || [];
    group.push(navEntry(item));
    canonical.set(definition.section, group);
  }

  if (auth.isAdmin && canNav("sources")) {
    const build = canonical.get("Build") || [];
    const at = build.findIndex((item) => item.id === "pdf");
    build.splice(Math.max(0, at + 1), 0, {
      id: "sources",
      label: i18n.t("nav.sources"),
      icon: "books",
      active: currentNavId.value === "sources",
    });
    canonical.set("Build", build);
  }

  if (auth.isAdmin) {
    const system = canonical.get("System") || [];
    const add = (entry: SidebarNavEntry) => {
      if (!system.some((item) => item.id === entry.id)) system.push(entry);
    };
    if (canNav("metadatamemory"))
      add({
        id: "metadatamemory",
        label: i18n.t("nav.metadatamemory"),
        icon: "spark",
        active: currentNavId.value === "metadatamemory",
      });
    if (canNav("users"))
      add({
        id: "users",
        label: i18n.t("nav.users"),
        icon: "users",
        active: currentNavId.value === "users",
      });
    if (canNav("roles"))
      add({
        id: "roles",
        label: i18n.t("nav.roles"),
        icon: "roles",
        active: currentNavId.value === "roles",
      });
    if (canNav("languages"))
      add({
        id: "languages",
        label: i18n.t("language.manage"),
        icon: "language",
        active: currentNavId.value === "languages",
      });
    add({
      id: "operations",
      label: i18n.t("ui.operations"),
      icon: "history",
      active: currentNavId.value === "operations",
    });
    canonical.set("System", system);
  }

  return ["Overview", ...NAV_SECTION_ORDER]
    .map((section) => ({
      section: sectionLabel(section),
      items: canonical.get(section) || [],
    }))
    .filter((group) => group.items.length);
});

function translatedRouteTitle() {
  if (route.name === "record" && s.value.context.title) return s.value.context.title;
  if (route.name === "settings-section") {
    const requested = String(route.params.section || "workspace");
    const id = isSettingsSectionId(requested) ? requested : "workspace";
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
      section === "Research"
        ? "/search"
        : section === "Corpora"
          ? "/works"
          : section === "Build"
            ? "/corpus-builder"
            : "/system-data/overview";
    items.push({ label: sectionLabel(section), to: sectionPath });
  }

  const parentKey = String(route.meta.breadcrumbParentKey || "");
  if (parentKey) {
    items.push({
      label: i18n.t(parentKey, String(route.meta.breadcrumbParentFallback || "")),
      to: "/system-data/overview",
    });
  } else if (route.name === "settings-section") {
    items.push({ label: i18n.t("nav.config", "Settings"), to: "/settings/workspace" });
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
  if (name === "compare") return i18n.t("context.compare.meta");
  if (name === "vector") return i18n.t("context.vector.meta");
  if (name === "corpus-builder" || name === "source-explorer") return i18n.t("context.pdf.meta");
  if (name === "providers") return i18n.t("context.providers.meta");
  if (name === "schemas") return i18n.t("schemas.manage_help");
  if (name.startsWith("system-data-")) return i18n.t("runtime.system_data_help");
  if (["users", "roles", "languages", "operations"].includes(name)) return "";
  return "";
});

const canBreadcrumbBack = computed(() => Boolean(nativeBackPath.value) || s.value.canGoBack);
const canBreadcrumbForward = computed(
  () => Boolean(nativeForwardPath.value) || s.value.canGoForward,
);
const breadcrumbBackLabel = computed(() =>
  nativeBackPath.value ? i18n.t("ui.back") : s.value.backLabel,
);
const breadcrumbForwardLabel = computed(() =>
  nativeForwardPath.value ? i18n.t("ui.forward") : s.value.forwardLabel,
);

function onImport(files: FileList) {
  if (auth.isAdmin) runtime.triggerImport(files);
}

function onFiles(event: Event) {
  const input = event.target as HTMLInputElement;
  if (input.files?.length) onImport(input.files);
  input.value = "";
}

function navigateNative(path: string, runtimeView?: string) {
  const current = router.currentRoute.value.fullPath;
  const target = router.resolve(path).fullPath;
  if (current === target) return;
  nativeBackPath.value = current;
  nativeForwardPath.value = null;
  if (runtimeView) {
    runtime.navigateView(runtimeView, target);
    return;
  }
  void router.push(target);
}

function navigate(view: string) {
  const target = NAV_TARGETS[view];
  if (!target) return;
  navigateNative(target.path, target.runtimeView);
}

function goBreadcrumbBack() {
  if (nativeBackPath.value) {
    const target = nativeBackPath.value;
    nativeForwardPath.value = router.currentRoute.value.fullPath;
    nativeBackPath.value = null;
    void router.push(target);
    return;
  }
  runtime.triggerBack();
}

function goBreadcrumbForward() {
  if (nativeForwardPath.value) {
    const target = nativeForwardPath.value;
    nativeBackPath.value = router.currentRoute.value.fullPath;
    nativeForwardPath.value = null;
    void router.push(target);
    return;
  }
  runtime.triggerForward();
}

function searchCorpus(query: string) {
  const value = query.trim();
  if (!value) return;
  topSearch.value = value;
  runtime.state.globalSearch = value;
  runtime.state.storeQuery = value;
  runtime.state.globalPage = 1;
  runtime.state.storeSearchResults = [];
  runtime.state.globalSearchMode = "traditional";
  runtime.navigateView("global");
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
  runtime.setUrlSyncHook((href: string, options: { replace?: boolean }) => {
    const target = router.resolve(href).fullPath;
    if (router.currentRoute.value.fullPath === target) return;
    const method = options?.replace ? router.replace : router.push;
    void method(target).catch(() => undefined);
  });
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
  runtime.pauseRuntime();
  runtimeStarted.value = false;
  await auth.logout();
  await router.replace("/");
}

async function handleAuthExpired() {
  if (handlingAuthExpiry.value || !auth.user) return;
  handlingAuthExpiry.value = true;
  try {
    runtime.pauseRuntime();
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
  window.addEventListener("derridai-auth-expired", () => {
    void handleAuthExpired();
  });
  window.addEventListener("derridai:permissions-changed", () => {
    void auth.loadStatus();
  });
  window.addEventListener("derridai:navigate-native", ((event: Event) => {
    const detail = (event as CustomEvent<{ path?: string; runtimeView?: string }>).detail || {};
    if (detail.path) navigateNative(detail.path, detail.runtimeView);
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

watch(
  () => auth.user?.id,
  (id) => {
    if (!id) {
      runtime.pauseRuntime();
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
    :class="{ 'sidebar-collapsed': s.sidebarCollapsed }"
  >
    <a class="skip-link" href="#appContent">{{ i18n.t("ui.skip_to_content") }}</a>
    <aside class="sidebar shell-sidebar">
      <SidebarBrand
        :collapsed="s.sidebarCollapsed"
        @navigate-home="navigate('home')"
        @toggle="runtime.toggleSidebar()"
      />
      <SidebarNavigator
        :groups="groupedNavItems"
        :collapsed="s.sidebarCollapsed"
        @navigate="navigate"
      />
      <div class="sidebar-spacer"></div>
      <SidebarStatus
        v-if="!s.sidebarCollapsed"
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
        <CommandSearch
          v-model="topSearch"
          shortcut=""
          :placeholder="i18n.t('ui.global_search_placeholder')"
          @submit="submitTopSearch"
        />
        <div class="shell-top-actions">
          <button
            class="shell-command-palette-button"
            type="button"
            :title="i18n.t('nav.command_palette')"
            :aria-label="i18n.t('nav.command_palette')"
            @click="commandPalette?.open()"
          >
            {{ i18n.t("nav.command_palette") }} <kbd>{{ commandShortcut }}</kbd>
          </button>
          <input
            id="fileInput"
            type="file"
            accept=".jsonl,.ndjson,.json,.zst"
            multiple
            hidden
            @change="onFiles"
          /><TopbarChrome
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
          <button
            class="breadcrumb-nav-button"
            type="button"
            :disabled="!canBreadcrumbBack"
            :title="breadcrumbBackLabel"
            :aria-label="i18n.t('ui.back')"
            @click="goBreadcrumbBack"
          >
            <span aria-hidden="true">←</span
            ><span class="breadcrumb-button-label">{{ i18n.t("ui.back") }}</span></button
          ><button
            class="breadcrumb-nav-button"
            type="button"
            :disabled="!canBreadcrumbForward"
            :title="breadcrumbForwardLabel"
            :aria-label="i18n.t('ui.forward')"
            @click="goBreadcrumbForward"
          >
            <span class="breadcrumb-button-label">{{ i18n.t("ui.forward") }}</span
            ><span aria-hidden="true">→</span>
          </button>
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
      <div id="appContent" class="app-content-region" tabindex="-1"><RouterView /></div>
    </section>
  </div>
  <NavigationCommandPalette
    ref="commandPalette"
    :groups="groupedNavItems"
    @navigate="navigate"
    @search="searchCorpus"
  />
  <LlmReviewWorkspace />
  <AppNotifications />
</template>

<style scoped>
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
  grid-template-columns: var(--ref-sidebar) minmax(0, 1fr);
  min-height: 100vh;
  background: var(--ref-bg);
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
@media (max-width: 900px) {
  .app-shell-modern {
    grid-template-columns: 64px minmax(0, 1fr);
  }
}
@media (max-width: 650px) {
  .app-shell-modern {
    display: block;
  }
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
