<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { onBeforeRouteLeave, useRoute, useRouter } from "vue-router";
import * as runtime from "../runtime/runtime.js";
import { apiRequest } from "../api/http";
import type { ProviderProfile } from "../api/system";
import { useAuthStore } from "../stores/auth";
import { useI18nStore } from "../stores/i18n";
import { useShellStore } from "../stores/shell";
import LanguageFlag from "../components/LanguageFlag.vue";
import UiButton from "../components/ui/UiButton.vue";
import UiDialog from "../components/ui/UiDialog.vue";
import UiField from "../components/ui/UiField.vue";
import UiHealthChip from "../components/ui/UiHealthChip.vue";
import SettingsNav from "../components/settings/SettingsNav.vue";
import SettingsSaveState from "../components/settings/SettingsSaveState.vue";
import SettingsSearch, { type SettingsSearchHit } from "../components/settings/SettingsSearch.vue";
import SettingsSection from "../components/settings/SettingsSection.vue";
import {
  APPEARANCE_DEFAULTS,
  RAG_DEFAULTS,
  SETTINGS_SECTIONS,
  cloneJson,
  filterSettingsFields,
  isSettingsSectionId,
  normalizeAppearance,
  normalizeEmbedding,
  normalizeRag,
  normalizeReview,
  sameSettings,
  validateRag,
  type AppearanceSettingsDraft,
  type EmbeddingSettingsDraft,
  type RagSettingsDraft,
  type ReviewSettingsDraft,
  type SaveStatus,
  type SettingsSectionId,
} from "../domain/settings";

type RuntimeSettings = {
  storageReady?: boolean;
  appConfig: Record<string, unknown>;
  ragConfig: Record<string, unknown>;
  health?: {chroma?: {path?: string}} | null;
  providerStatuses?: Record<string, {available?: boolean; checked_at?: string; error?: string}>;
  files?: unknown[];
  sidebarCollapsed?: boolean;
  tableColumns?: Record<string, unknown>;
  collapsedPanels?: Record<string, unknown>;
  upsertIgnored?: Record<string, unknown>;
  jobs?: Array<{status?: string}>;
};
const workspace = runtime.state as RuntimeSettings;
const auth = useAuthStore();
const i18n = useI18nStore();
const shell = useShellStore();
const route = useRoute();
const router = useRouter();

const appearanceSaved = ref(normalizeAppearance(workspace.appConfig as unknown as AppearanceSettingsDraft));
const appearanceDraft = ref(cloneJson(appearanceSaved.value));
const reviewSaved = ref(normalizeReview(workspace.appConfig as unknown as ReviewSettingsDraft));
const reviewDraft = ref(cloneJson(reviewSaved.value));
const embeddingSaved = ref(normalizeEmbedding(workspace.appConfig as unknown as EmbeddingSettingsDraft));
const embeddingDraft = ref(cloneJson(embeddingSaved.value));
const ragSaved = ref(normalizeRag(workspace.ragConfig as unknown as RagSettingsDraft));
const ragDraft = ref(cloneJson(ragSaved.value));
const notificationsOn = ref(Boolean(workspace.appConfig.desktop_notifications));
const nukePhrase = ref("");
const query = ref("");
const advancedOpen = ref(false);
const contentsOpen = ref(false);
const liveMessage = ref("");
const pageError = ref("");
const ragErrors = ref<Record<string, string>>({});
const groupStatus = ref<Record<string, SaveStatus>>({appearance: "saved", review: "saved", embedding: "saved", rag: "saved"});
const confirm = ref<{kind: "backup" | "restore" | "updates" | "nuke" | "leave"; title: string; message: string} | null>(null);
const restoreFile = ref<File | null>(null);
const restoreInput = ref<HTMLInputElement | null>(null);
const routeGuardResolve = ref<((allow: boolean) => void) | null>(null);
const busy = ref("");

const isAdmin = computed(() => auth.isAdmin);
const canAppearance = computed(() => auth.can("appearance.manage") || isAdmin.value);
const chromaPath = computed(() => String(workspace.health?.chroma?.path || "/data/chroma"));
const profiles = computed(() => (runtime.getProviderProfilesForUi?.() || []) as ProviderProfile[]);
const defaultProfileId = computed(() => String(runtime.getDefaultProviderProfileId?.() || reviewDraft.value.default_provider_profile));
const localeInfo = computed(() => i18n.languages.find(item => item.code === i18n.locale));
const visibleSections = computed(() => {
  const ids: SettingsSectionId[] = ["workspace", "language"];
  if (isAdmin.value) ids.push("research", "review", "providers", "retrieval", "security", "system");
  else ids.push("research");
  return SETTINGS_SECTIONS.filter(section => ids.includes(section.id)).map(section => ({
    id: section.id,
    label: i18n.t(section.labelKey, section.labelFallback),
    description: i18n.t(section.descriptionKey, section.descriptionFallback),
  }));
});
const section = computed<SettingsSectionId>({
  get() {
    const raw = String(route.query.section || "workspace");
    const requested = isSettingsSectionId(raw) ? raw : "workspace";
    return visibleSections.value.some(item => item.id === requested) ? requested : visibleSections.value[0]?.id || "workspace";
  },
  set(id) { void router.replace({path: "/settings", query: {...route.query, section: id}}); },
});
const appearanceDirty = computed(() => !sameSettings(appearanceDraft.value, appearanceSaved.value));
const reviewDirty = computed(() => !sameSettings(reviewDraft.value, reviewSaved.value));
const embeddingDirty = computed(() => !sameSettings(embeddingDraft.value, embeddingSaved.value));
const ragDirty = computed(() => !sameSettings(ragDraft.value, ragSaved.value));
const dirty = computed(() => appearanceDirty.value || reviewDirty.value || embeddingDirty.value || ragDirty.value);
const pageStatus = computed<SaveStatus>(() => {
  const values = Object.values(groupStatus.value);
  if (values.includes("failed")) return "failed";
  if (values.includes("saving")) return "saving";
  if (values.includes("success")) return "success";
  if (dirty.value) return "dirty";
  return "saved";
});
const searchHits = computed<SettingsSearchHit[]>(() => {
  const fields = filterSettingsFields(query.value, (key, fallback) => i18n.t(key, fallback));
  const allowed = new Set(visibleSections.value.map(item => item.id));
  return fields.filter(field => allowed.has(field.section)).map(field => ({
    id: field.id,
    section: field.section,
    label: i18n.t(field.labelKey, field.labelFallback),
    group: i18n.t(SETTINGS_SECTIONS.find(item => item.id === field.section)?.labelKey || "", field.section),
  }));
});
const backupCounts = computed(() => ({
  files: Number(workspace.files?.length || 0),
  jobs: (workspace.jobs || []).filter(job => ["queued", "running", "cancelling"].includes(String(job.status))).length,
}));

function persistKind(kind: "browser" | "readonly" | "link" | "backend") {
  if (kind === "readonly") return i18n.t("settings.persist.readonly", "Read-only");
  if (kind === "link") return i18n.t("settings.persist.link", "Managed elsewhere");
  if (kind === "backend") return i18n.t("settings.persist.backend", "Server operation");
  return i18n.t("settings.persist.browser", "Saved in this browser");
}
function statusLabel(status: SaveStatus) {
  if (status === "dirty") return i18n.t("settings.status.unsaved", "Unsaved changes");
  if (status === "saving") return i18n.t("settings.status.saving", "Saving");
  if (status === "success") return i18n.t("settings.status.saved_ok", "Save succeeded");
  if (status === "failed") return i18n.t("settings.status.save_failed", "Save failed");
  if (status === "readonly") return i18n.t("settings.status.readonly", "Read-only");
  return i18n.t("settings.status.saved", "Saved");
}
function announce(message: string) { liveMessage.value = message; }
function mark(group: string, status: SaveStatus) { groupStatus.value = {...groupStatus.value, [group]: status}; }
async function persistWorkspace() {
  if (typeof runtime.flushWorkspacePrefs === "function") await runtime.flushWorkspacePrefs();
  else runtime.persistPrefs();
  shell.sync();
}
async function saveGroup(group: string, apply: () => void) {
  pageError.value = "";
  mark(group, "saving");
  announce(i18n.t("settings.status.saving", "Saving"));
  const previousApp = cloneJson(workspace.appConfig);
  const previousRag = cloneJson(workspace.ragConfig);
  const previousAppearance = cloneJson(appearanceSaved.value);
  const previousReview = cloneJson(reviewSaved.value);
  const previousEmbedding = cloneJson(embeddingSaved.value);
  const previousRagSaved = cloneJson(ragSaved.value);
  try {
    apply();
    await persistWorkspace();
    mark(group, "success");
    announce(i18n.t("settings.status.saved_ok", "Save succeeded"));
    window.setTimeout(() => { if (groupStatus.value[group] === "success") mark(group, "saved"); }, 1600);
  } catch (error) {
    Object.assign(workspace.appConfig, previousApp);
    Object.assign(workspace.ragConfig, previousRag);
    appearanceSaved.value = previousAppearance;
    reviewSaved.value = previousReview;
    embeddingSaved.value = previousEmbedding;
    ragSaved.value = previousRagSaved;
    mark(group, "failed");
    pageError.value = error instanceof Error ? error.message : String(error);
    announce(i18n.t("settings.status.save_failed", "Save failed"));
  }
}
function saveAppearance() {
  void saveGroup("appearance", () => {
    appearanceDraft.value = normalizeAppearance(appearanceDraft.value);
    runtime.applyAppearance(appearanceDraft.value);
    Object.assign(workspace.appConfig, appearanceDraft.value);
    appearanceSaved.value = cloneJson(appearanceDraft.value);
  });
}
function saveReview() {
  void saveGroup("review", () => {
    reviewDraft.value = normalizeReview(reviewDraft.value);
    const profile = profiles.value.find(item => item.id === reviewDraft.value.default_provider_profile);
    workspace.appConfig.default_provider_profile = reviewDraft.value.default_provider_profile;
    if (profile) workspace.appConfig.chat_provider = profile.type;
    workspace.appConfig.default_review_preset = reviewDraft.value.default_review_preset;
    workspace.appConfig.default_llm_run_mode = reviewDraft.value.default_llm_run_mode;
    reviewSaved.value = cloneJson(reviewDraft.value);
  });
}
function saveEmbedding() {
  void saveGroup("embedding", () => {
    embeddingDraft.value = normalizeEmbedding(embeddingDraft.value);
    Object.assign(workspace.appConfig, embeddingDraft.value);
    embeddingSaved.value = cloneJson(embeddingDraft.value);
  });
}
function saveRag() {
  ragDraft.value = normalizeRag(ragDraft.value);
  const errors = validateRag(ragDraft.value);
  ragErrors.value = Object.fromEntries(errors.map(error => [error.field, i18n.t(error.messageKey, error.messageFallback)]));
  if (errors.length) {
    mark("rag", "failed");
    announce(i18n.t("settings.validation_summary", "Some retrieval defaults could not be saved."));
    void nextTick(() => document.querySelector<HTMLElement>(".settings-section .ui-field.invalid input, .settings-section .ui-field.invalid select")?.focus());
    return;
  }
  void saveGroup("rag", () => {
    Object.assign(workspace.ragConfig, ragDraft.value);
    ragSaved.value = cloneJson(ragDraft.value);
  });
}
function resetAppearance() {
  appearanceDraft.value = cloneJson(APPEARANCE_DEFAULTS);
  saveAppearance();
}
function resetRag() {
  ragDraft.value = cloneJson(RAG_DEFAULTS);
  saveRag();
}
async function setLocale(code: string) {
  await i18n.setLocale(code);
  announce(i18n.tf("settings.language_changed", "Interface language is now {name}.", {name: i18n.languages.find(item => item.code === code)?.name || code}));
}
function goSection(id: SettingsSectionId) {
  section.value = id;
  contentsOpen.value = false;
  void nextTick(() => document.getElementById(`settings-section-${id}`)?.scrollIntoView({block: "start"}));
}
function chooseSearch(hit: SettingsSearchHit) {
  goSection(hit.section);
  query.value = "";
  void nextTick(() => document.getElementById(`settings-field-${hit.id}`)?.focus?.() || document.getElementById(`settings-section-${hit.section}`)?.scrollIntoView({block: "start"}));
}
function go(path: string, view?: string) {
  if (view) runtime.navigateView(view);
  else window.dispatchEvent(new CustomEvent("derridai:navigate-native", {detail: {path}}));
}
function providerReady(profile: ProviderProfile) {
  const status = workspace.providerStatuses?.[profile.id];
  return Boolean(status?.available);
}
function providerChecked(profile: ProviderProfile) {
  const stamp = workspace.providerStatuses?.[profile.id]?.checked_at;
  if (!stamp) return i18n.t("settings.not_checked", "Not checked yet");
  const date = new Date(stamp);
  return Number.isNaN(date.getTime()) ? stamp : date.toLocaleString(i18n.locale);
}
async function saveNotifications() {
  workspace.appConfig.desktop_notifications = notificationsOn.value;
  await persistWorkspace();
  announce(i18n.t("settings.notifications_saved", "Notification preference saved"));
}
async function requestNotifications() {
  if (typeof Notification === "undefined") {
    pageError.value = i18n.t("settings.notifications_unsupported", "Desktop notifications are not supported by this browser.");
    return;
  }
  try {
    const permission = await Notification.requestPermission();
    notificationsOn.value = permission === "granted";
    await saveNotifications();
    announce(permission === "granted" ? i18n.t("settings.notifications_enabled", "Desktop notifications enabled") : i18n.tf("settings.notifications_permission", "Notification permission: {status}", {status: permission}));
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : String(error);
  }
}
function resetColumns() { workspace.tableColumns = {}; runtime.persistPrefs(); announce(i18n.t("settings.columns_reset", "Table columns reset")); }
function expandPanels() { workspace.collapsedPanels = {}; runtime.persistPrefs(); announce(i18n.t("settings.panels_expanded", "All UI panels expanded")); }
function expandSidebar() {
  if (workspace.sidebarCollapsed) runtime.toggleSidebar();
  announce(i18n.t("settings.sidebar_expanded", "Navigation sidebar expanded"));
}
function clearUpsertSuppressions() { workspace.upsertIgnored = {}; runtime.persistPrefs(); announce(i18n.t("settings.upsert_restored", "Removed upsert-queue items restored")); }
function openBackup() {
  confirm.value = {
    kind: "backup",
    title: i18n.t("settings.backup_confirm_title", "Create full backup?"),
    message: runtime.backupContainsCredentials?.()
      ? i18n.t("settings.backup_keys_warning", "This full backup can contain provider API keys. Store the ZIP securely. Installed model files are not copied.")
      : i18n.t("settings.backup_confirm_message", "Create a full backup of this workspace, records, configuration, and vector collections."),
  };
}
function openRestore() { restoreInput.value?.click(); }
function onRestoreFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0] || null;
  input.value = "";
  if (!file) return;
  restoreFile.value = file;
  confirm.value = {
    kind: "restore",
    title: i18n.t("settings.restore_confirm_title", "Restore full DerridAI backup?"),
    message: i18n.t("settings.restore_confirm_message", "This replaces the current browser workspace and every collection in the active Chroma database."),
  };
}
function openUpdates() {
  confirm.value = {kind: "updates", title: i18n.t("settings.clear_updates_title", "Clear all update histories?"), message: i18n.t("settings.clear_updates_message", "This permanently removes local audit histories from loaded records.")};
}
function openNuke() {
  confirm.value = {kind: "nuke", title: i18n.t("config.nuke.confirm_title", "Reset DerridAI to a fresh install?"), message: i18n.t("config.nuke.confirm_message", "This returns DerridAI to a first-run state: users, corpora, PDF builds, vector collections, provider profiles, annotations, jobs, and this browser workspace are deleted. You will create a new administrator account. Installed model files are not deleted.")};
}
async function applyConfirm() {
  const kind = confirm.value?.kind;
  if (!kind) return;
  busy.value = kind;
  pageError.value = "";
  try {
    if (kind === "backup") await runtime.downloadFullBackup({confirmed: true});
    else if (kind === "restore" && restoreFile.value) await runtime.restoreFullBackup(restoreFile.value, {confirmed: true});
    else if (kind === "updates") await runtime.clearAllUpdates({confirmed: true});
    else if (kind === "nuke") {
      await apiRequest("/api/admin/nuke", {method: "POST", body: "{}"});
      await runtime.deleteAllDerridaiBrowserState();
      location.reload();
      return;
    } else if (kind === "leave") {
      const resolve = routeGuardResolve.value;
      routeGuardResolve.value = null;
      confirm.value = null;
      resolve?.(true);
      return;
    }
    confirm.value = null;
    announce(i18n.t("settings.action_complete", "Action completed"));
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : String(error);
    if (kind === "nuke") pageError.value = i18n.tf("config.nuke.failed", "Nuke failed: {error}", {error: pageError.value});
  } finally { busy.value = ""; }
}
function closeConfirm() {
  if (busy.value) return;
  confirm.value = null;
  restoreFile.value = null;
  const resolve = routeGuardResolve.value;
  routeGuardResolve.value = null;
  resolve?.(false);
}
function onBeforeUnload(event: BeforeUnloadEvent) {
  if (!dirty.value) return;
  event.preventDefault();
  event.returnValue = "";
}
onBeforeRouteLeave(() => {
  if (!dirty.value) return true;
  return new Promise<boolean>(resolve => {
    routeGuardResolve.value = resolve;
    confirm.value = {kind: "leave", title: i18n.t("settings.leave_title", "Discard unsaved settings?"), message: i18n.t("settings.leave_message", "Your unsaved Settings changes will be lost if you leave this page.")};
  });
});
watch(appearanceDraft, value => runtime.applyAppearance(normalizeAppearance(value)), {deep: true});
watch([appearanceDirty, reviewDirty, embeddingDirty, ragDirty], () => {
  if (appearanceDirty.value) mark("appearance", "dirty");
  if (reviewDirty.value) mark("review", "dirty");
  if (embeddingDirty.value) mark("embedding", "dirty");
  if (ragDirty.value) mark("rag", "dirty");
});
onMounted(() => {
  window.addEventListener("beforeunload", onBeforeUnload);
  appearanceSaved.value = normalizeAppearance(workspace.appConfig as unknown as AppearanceSettingsDraft);
  appearanceDraft.value = cloneJson(appearanceSaved.value);
  reviewSaved.value = normalizeReview(workspace.appConfig as unknown as ReviewSettingsDraft);
  reviewDraft.value = cloneJson(reviewSaved.value);
  embeddingSaved.value = normalizeEmbedding(workspace.appConfig as unknown as EmbeddingSettingsDraft);
  embeddingDraft.value = cloneJson(embeddingSaved.value);
  ragSaved.value = normalizeRag(workspace.ragConfig as unknown as RagSettingsDraft);
  ragDraft.value = cloneJson(ragSaved.value);
  notificationsOn.value = Boolean(workspace.appConfig.desktop_notifications);
  runtime.applyAppearance(appearanceDraft.value);
});
onBeforeUnmount(() => window.removeEventListener("beforeunload", onBeforeUnload));
</script>

<template>
  <main class="vue-native-page settings-page">
    <div class="sr-only" aria-live="polite">{{ liveMessage }}</div>
    <header class="settings-hero">
      <div>
        <p class="settings-kicker">{{ i18n.t("section.system", "System") }}</p>
        <h1>{{ i18n.t("context.config.title", "Settings") }}</h1>
        <p>{{ i18n.t("settings.page_help", "Control workspace appearance, research defaults, and operational tools. Each group saves on its own; leaving with unsaved changes will ask for confirmation.") }}</p>
      </div>
      <SettingsSaveState :status="pageStatus" :label="statusLabel(pageStatus)" />
    </header>
    <p v-if="pageError" class="info error" role="alert">{{ pageError }}</p>
    <div class="settings-toolbar">
      <SettingsSearch
        v-model="query"
        :results="searchHits"
        :label="i18n.t('settings.search_label', 'Search settings')"
        :placeholder="i18n.t('settings.search_placeholder', 'Find a setting')"
        described-by="settings-search-help"
        :no-results="i18n.t('settings.search_empty', 'No settings match that search.')"
        :result-count="i18n.tf(searchHits.length === 1 ? 'settings.search_count_one' : 'settings.search_count_many', searchHits.length === 1 ? '{count} matching setting' : '{count} matching settings', {count: searchHits.length})"
        @choose="chooseSearch"
      />
      <p id="settings-search-help" class="note">{{ i18n.t("settings.search_help", "Search uses translated labels. Arrow keys move through matches; Enter opens the section.") }}</p>
      <UiButton class="settings-contents-toggle" :label="i18n.t('settings.contents', 'Contents')" :pressed="contentsOpen" @click="contentsOpen = !contentsOpen" />
    </div>
    <div class="settings-layout">
      <aside class="settings-rail" :class="{open: contentsOpen}">
        <SettingsNav v-model="section" :items="visibleSections" :tablist-label="i18n.t('settings.contents', 'Contents')" @select="goSection" />
      </aside>
      <div class="settings-pane">
        <div v-show="section === 'workspace'" id="settings-section-workspace" role="tabpanel" aria-labelledby="settings-nav-workspace">
          <SettingsSection section-id="workspace" :title="i18n.t('settings.appearance', 'Appearance')" :description="i18n.t('settings.appearance_help', 'Choose the interface color theme for your workspace.')" :persistence="persistKind('browser')" :status="groupStatus.appearance" :status-label="statusLabel(groupStatus.appearance)">
            <fieldset v-if="canAppearance" class="theme-choice-grid" :disabled="!canAppearance">
              <legend>{{ i18n.t("settings.color_theme", "Color theme") }}</legend>
              <label v-for="theme in (['green','blue','slate'] as const)" :key="theme" class="theme-choice" :class="{selected: appearanceDraft.ui_color_theme === theme}">
                <input type="radio" name="settingsTheme" :value="theme" v-model="appearanceDraft.ui_color_theme">
                <span class="theme-swatch" :class="`theme-swatch-${theme}`" aria-hidden="true"><i></i><i></i><i></i></span>
                <span><b>{{ i18n.t(`settings.theme_${theme}`, theme) }}</b><small>{{ theme === 'green' ? i18n.t('settings.theme_green_help', 'The original restrained green palette.') : theme === 'blue' ? i18n.t('settings.theme_blue_help', 'The blue palette used in the visual reference.') : i18n.t('settings.theme_slate_help', 'A neutral graphite-blue research palette.') }}</small></span>
              </label>
            </fieldset>
            <p v-else class="note">{{ i18n.t("settings.appearance_unavailable", "Your role cannot change workspace appearance.") }}</p>
            <div class="config-grid">
              <UiField :label="i18n.t('settings.color_scheme', 'Color scheme')" :hint="i18n.t('settings.color_scheme_help', 'Light, dark, or follow this device. Stored in this browser.')" :persistence="persistKind('browser')">
                <select id="settings-field-scheme" class="control" v-model="appearanceDraft.ui_color_scheme">
                  <option value="system">{{ i18n.t("settings.scheme_system", "Match device") }}</option>
                  <option value="light">{{ i18n.t("settings.scheme_light", "Light") }}</option>
                  <option value="dark">{{ i18n.t("settings.scheme_dark", "Dark") }}</option>
                </select>
              </UiField>
              <UiField :label="i18n.t('settings.contrast', 'Contrast')" :hint="i18n.t('settings.contrast_help', 'Increase contrast for borders and muted text in this workspace.')">
                <select id="settings-field-contrast" class="control" v-model="appearanceDraft.ui_contrast">
                  <option value="system">{{ i18n.t("settings.contrast_system", "Match device") }}</option>
                  <option value="more">{{ i18n.t("settings.contrast_more", "More contrast") }}</option>
                </select>
              </UiField>
            </div>
            <template #actions>
              <UiButton variant="primary" icon="check" :label="i18n.t('settings.save_appearance', 'Save appearance')" :disabled="!canAppearance || groupStatus.appearance === 'saving'" @click="saveAppearance" />
              <UiButton :label="i18n.t('settings.reset_appearance', 'Reset appearance defaults')" :disabled="!canAppearance" @click="resetAppearance" />
            </template>
          </SettingsSection>
        </div>

        <div v-show="section === 'language'" id="settings-section-language" role="tabpanel" aria-labelledby="settings-nav-language">
          <SettingsSection section-id="language" :title="i18n.t('settings.language_title', 'Language and accessibility')" :description="i18n.t('settings.language_help', 'The interface language applies immediately. Dictionaries are edited on the Languages page.')" :persistence="persistKind('browser')" status="saved" :status-label="statusLabel('saved')">
            <UiField :label="i18n.t('settings.interface_language', 'Interface language')" :hint="i18n.t('settings.interface_language_help', 'Applies immediately to labels, dates, and numbers in this browser.')">
              <div class="settings-locale-row">
                <LanguageFlag :code="i18n.locale" :symbol="localeInfo?.flag" :label="localeInfo?.name" size="small" />
                <select id="settings-field-locale" class="control" :value="i18n.locale" :disabled="i18n.loading" :aria-busy="i18n.loading" @change="setLocale(($event.target as HTMLSelectElement).value)">
                  <option v-for="language in i18n.languages" :key="language.code" :value="language.code">{{ language.name }}</option>
                </select>
              </div>
            </UiField>
            <p class="note">{{ i18n.t("settings.a11y_note", "Focus indicators stay visible in every theme. Motion is reduced when this device requests it. High-contrast mode uses stronger borders rather than color alone.") }}</p>
            <template v-if="isAdmin" #actions>
              <UiButton icon="language" :label="i18n.t('language.manage', 'Manage languages')" @click="go('/languages')" />
            </template>
          </SettingsSection>
        </div>

        <div v-show="section === 'research'" id="settings-section-research" role="tabpanel" aria-labelledby="settings-nav-research">
          <SettingsSection v-if="isAdmin" section-id="research" :title="i18n.t('settings.research_title', 'Research defaults')" :description="i18n.t('settings.research_help', 'Response language and evidence presentation defaults. Per-run generation still lives on Research.')" :persistence="persistKind('browser')" :status="groupStatus.rag" :status-label="statusLabel(groupStatus.rag)">
            <UiField :label="i18n.t('settings.rag_response_language', 'Response language')" :hint="i18n.t('settings.rag_response_language_help', 'Guides generated answers. Source language tags on records are unchanged.')">
              <select id="settings-field-rag-response-language" class="control" v-model="ragDraft.response_language">
                <option value="auto">{{ i18n.t("settings.lang_auto", "Auto") }}</option>
                <option value="en">{{ i18n.t("settings.lang_en", "English") }}</option>
                <option value="fr">{{ i18n.t("settings.lang_fr", "French") }}</option>
              </select>
            </UiField>
            <template #actions>
              <UiButton variant="primary" :label="i18n.t('settings.save_research', 'Save research defaults')" @click="saveRag" />
              <UiButton icon="spark" :label="i18n.t('nav.rag', 'Research')" @click="go('/rag', 'rag')" />
            </template>
          </SettingsSection>
          <SettingsSection v-else section-id="research" :title="i18n.t('settings.researcher_workspace', 'Research workspace')" :description="i18n.t('settings.researcher_workspace_help', 'Researcher accounts use summarized corpus text and do not expose database or source-management controls.')" :persistence="persistKind('readonly')" status="readonly" :status-label="statusLabel('readonly')">
            <div class="config-actions">
              <UiButton v-if="auth.can('page.dashboard')" icon="dashboard" :label="i18n.t('nav.home', 'Home')" @click="go('/', 'home')" />
              <UiButton v-if="auth.can('page.annotations')" icon="record" :label="i18n.t('nav.annotations', 'Annotations')" @click="go('/annotations', 'annotations')" />
              <UiButton v-if="auth.can('page.research')" icon="spark" :label="i18n.t('nav.rag', 'Research')" @click="go('/rag', 'rag')" />
            </div>
            <p v-if="!auth.can('page.dashboard') && !auth.can('page.annotations') && !auth.can('page.research')" class="note">{{ i18n.t("permissions.no_workspace_shortcuts", "No additional workspace pages are enabled for this role.") }}</p>
          </SettingsSection>
        </div>

        <div v-if="isAdmin" v-show="section === 'review'" id="settings-section-review" role="tabpanel" aria-labelledby="settings-nav-review">
          <SettingsSection section-id="review" :title="i18n.t('settings.review_title', 'Review and AI behavior')" :description="i18n.t('settings.review_help', 'Provider choice, default review preset, and whether LLM review opens interactively or runs as a background job.')" :persistence="persistKind('browser')" :status="groupStatus.review" :status-label="statusLabel(groupStatus.review)">
            <div class="config-grid">
              <UiField :label="i18n.t('settings.default_provider', 'Default provider profile')" :hint="i18n.t('settings.default_provider_help', 'Used when a workflow does not pick a profile itself. Credentials stay on the Providers page.')">
                <select id="settings-field-review-provider" class="control" v-model="reviewDraft.default_provider_profile">
                  <option v-if="!profiles.length" value="">{{ i18n.t("settings.not_configured", "Not configured") }}</option>
                  <option v-for="profile in profiles" :key="profile.id" :value="profile.id">{{ profile.name || profile.id }} · {{ profile.type === "ollama" ? "Ollama" : i18n.t("settings.openai_compatible", "OpenAI-compatible") }}</option>
                </select>
              </UiField>
              <UiField :label="i18n.t('settings.review_preset', 'Default review preset')">
                <select id="settings-field-review-preset" class="control" v-model="reviewDraft.default_review_preset">
                  <option value="text">{{ i18n.t("settings.preset_text", "OCR / text cleanup") }}</option>
                  <option value="attribution">{{ i18n.t("settings.preset_attribution", "Attribution") }}</option>
                  <option value="semantic">{{ i18n.t("settings.preset_semantic", "Semantics") }}</option>
                </select>
              </UiField>
              <UiField :label="i18n.t('settings.run_mode', 'Default run mode')" :hint="i18n.t('settings.run_mode_help', 'Interactive review stays on screen. Background review is cancellable from Operations.')">
                <select id="settings-field-review-mode" class="control" v-model="reviewDraft.default_llm_run_mode">
                  <option value="foreground">{{ i18n.t("settings.run_foreground", "Interactive foreground") }}</option>
                  <option value="background">{{ i18n.t("settings.run_background", "Background review") }}</option>
                </select>
              </UiField>
              <label class="check-item field-full"><input id="settings-field-rag-auto-grade" type="checkbox" v-model="ragDraft.auto_grade"><span>{{ i18n.t("settings.rag_auto_grade", "Auto-grade the final research response after caching") }}<small>{{ i18n.t("settings.rag_auto_grade_help", "Choose the grading provider on Research. Self-grading is warned there.") }}</small></span></label>
            </div>
            <template #actions>
              <UiButton variant="primary" icon="check" :label="i18n.t('settings.save_review', 'Save review behavior')" @click="saveReview(); if (ragDirty) saveRag()" />
            </template>
          </SettingsSection>
        </div>

        <div v-if="isAdmin" v-show="section === 'providers'" id="settings-section-providers" role="tabpanel" aria-labelledby="settings-nav-providers">
          <SettingsSection section-id="providers" :title="i18n.t('settings.providers_title', 'Providers and models')" :description="i18n.t('settings.providers_help', 'Endpoints, credentials, models, concurrency limits, and warmups are configured on the dedicated Providers page. Secrets are never shown here.')" :persistence="persistKind('link')" status="readonly" :status-label="statusLabel('readonly')">
            <ul v-if="profiles.length" class="providers-summary">
              <li v-for="profile in profiles" :key="profile.id">
                <UiHealthChip :available="providerReady(profile)" :label="String(profile.name || profile.id)" :detail="providerReady(profile) ? i18n.t('settings.provider_ready', 'Ready') : i18n.t('settings.provider_not_ready', 'Not ready')" />
                <span>{{ profile.type === "ollama" ? i18n.t("settings.provider_ollama", "Ollama") : i18n.t("settings.openai_compatible", "OpenAI-compatible") }} · {{ i18n.tf("settings.max_concurrent", "max {count}", {count: Number(profile.max_concurrent_requests ?? 1)}) }} · {{ profile.model || i18n.t("language.model_not_set", "model not set") }}</span>
                <small>{{ i18n.tf("settings.last_checked", "Last checked: {time}", {time: providerChecked(profile)}) }}</small>
                <b v-if="profile.id === defaultProfileId">{{ i18n.t("ui.default", "Default") }}</b>
              </li>
            </ul>
            <p v-else class="note">{{ i18n.t("settings.no_providers", "No LLM provider profiles are configured.") }}</p>
            <template #actions>
              <UiButton variant="primary" icon="spark" :label="i18n.t('settings.open_providers', 'Open LLM Providers')" @click="go('/providers', 'providers')" />
            </template>
          </SettingsSection>
        </div>

        <div v-if="isAdmin" v-show="section === 'retrieval'" id="settings-section-retrieval" role="tabpanel" aria-labelledby="settings-nav-retrieval">
          <SettingsSection section-id="retrieval" :title="i18n.t('settings.vector_title', 'Vector database defaults')" :description="i18n.t('settings.vector_help', 'New collections default to Ollama embeddings with bge-m3:latest. Changing a collection that already contains records requires a new build.')" :persistence="persistKind('browser')" :status="groupStatus.embedding" :status-label="statusLabel(groupStatus.embedding)">
            <div class="config-grid">
              <UiField :label="i18n.t('settings.embedding_provider', 'Default embedding provider')">
                <select id="settings-field-embedding-provider" class="control" v-model="embeddingDraft.embedding_provider">
                  <option value="ollama">{{ i18n.t("settings.provider_ollama", "Ollama") }}</option>
                  <option value="chroma">{{ i18n.t("vector.provider_chroma", "Chroma default") }}</option>
                  <option value="precomputed">{{ i18n.t("vector.provider_precomputed", "Precomputed vectors") }}</option>
                </select>
              </UiField>
              <UiField :label="i18n.t('settings.embedding_model', 'Default embedding model')">
                <input id="settings-field-embedding-model" class="control" v-model="embeddingDraft.embedding_model">
              </UiField>
              <UiField wide :label="i18n.t('settings.chroma_path', 'Current Chroma path')" :hint="i18n.t('settings.chroma_path_help', 'Reported by the running API. Change the backend on Vector Stores.')" :persistence="persistKind('readonly')">
                <input id="settings-field-chroma-path" class="control" :value="chromaPath" readonly>
              </UiField>
            </div>
            <template #actions>
              <UiButton variant="primary" :label="i18n.t('settings.save_embedding', 'Save embedding defaults')" @click="saveEmbedding" />
              <UiButton icon="database" :label="i18n.t('nav.vector', 'Vector Stores')" @click="go('/databases', 'vector')" />
            </template>
          </SettingsSection>
          <SettingsSection section-id="rag" :title="i18n.t('settings.rag_title', 'RAG pipeline defaults')" :description="i18n.t('settings.rag_help', 'Retrieval, fusion, reranking, and evidence-budget defaults. These values are stored with each run so later audit can reproduce it.')" :persistence="persistKind('browser')" :status="groupStatus.rag" :status-label="statusLabel(groupStatus.rag)">
            <p v-if="Object.keys(ragErrors).length" class="info error" role="alert">{{ i18n.t("settings.validation_summary", "Some retrieval defaults could not be saved.") }}</p>
            <div class="config-grid">
              <UiField :label="i18n.t('settings.rag_k', 'Retrieval k')" :hint="i18n.t('settings.rag_k_help', 'How many passages to keep after ranking. Typical scholarly runs use 24–64.')" :error="ragErrors.k">
                <input id="settings-field-rag-k" class="control" type="number" min="1" max="500" v-model.number="ragDraft.k" :aria-invalid="Boolean(ragErrors.k)">
              </UiField>
              <UiField :label="i18n.t('settings.rag_top_n', 'Rerank top N')" :hint="i18n.t('settings.rag_top_n_help', 'How many candidates the reranker inspects.')">
                <input id="settings-field-rag-top-n" class="control" type="number" min="1" max="500" v-model.number="ragDraft.rerank_top_n">
              </UiField>
              <UiField :label="i18n.t('settings.rag_reranker', 'Default reranker')">
                <select id="settings-field-rag-reranker" class="control" v-model="ragDraft.reranker">
                  <option value="cross_encoder">{{ i18n.t("settings.reranker_ce", "Cross-encoder") }}</option>
                  <option value="lexical">{{ i18n.t("settings.reranker_lexical", "Lexical/vector") }}</option>
                  <option value="none">{{ i18n.t("settings.reranker_none", "None") }}</option>
                </select>
              </UiField>
              <UiField :label="i18n.t('settings.rag_record_chars', 'Max characters per evidence record')" :hint="i18n.t('settings.rag_record_chars_help', 'Caps each passage so the model cannot swallow an entire chapter as one evidence item.')">
                <input id="settings-field-rag-record-chars" class="control" type="number" min="500" v-model.number="ragDraft.evidence_record_char_limit">
              </UiField>
              <UiField :label="i18n.t('settings.rag_total_chars', 'Total evidence characters')" :error="ragErrors.evidence_total_char_limit">
                <input id="settings-field-rag-total-chars" class="control" type="number" min="5000" v-model.number="ragDraft.evidence_total_char_limit" :aria-invalid="Boolean(ragErrors.evidence_total_char_limit)">
              </UiField>
              <fieldset class="field field-full">
                <legend>{{ i18n.t("settings.rag_locales", "Document languages") }}</legend>
                <div class="language-checks">
                  <label><input id="settings-field-rag-locale-en" type="checkbox" value="en" :checked="ragDraft.locales.includes('en')" @change="ragDraft.locales = ($event.target as HTMLInputElement).checked ? [...new Set([...ragDraft.locales, 'en'])] : ragDraft.locales.filter(code => code !== 'en')"><span>{{ i18n.t("settings.lang_en", "English") }}</span></label>
                  <label><input id="settings-field-rag-locale-fr" type="checkbox" value="fr" :checked="ragDraft.locales.includes('fr')" @change="ragDraft.locales = ($event.target as HTMLInputElement).checked ? [...new Set([...ragDraft.locales, 'fr'])] : ragDraft.locales.filter(code => code !== 'fr')"><span>{{ i18n.t("settings.lang_fr", "French") }}</span></label>
                </div>
                <p v-if="ragErrors.locales" class="ui-field-error" role="alert">{{ ragErrors.locales }}</p>
              </fieldset>
              <fieldset class="field field-full">
                <legend>{{ i18n.t("settings.rag_routes", "Retrieval routes") }}</legend>
                <div class="language-checks">
                  <label><input type="checkbox" :checked="ragDraft.search_types.includes('similarity')" @change="ragDraft.search_types = ($event.target as HTMLInputElement).checked ? [...new Set([...ragDraft.search_types, 'similarity' as const])] : ragDraft.search_types.filter(item => item !== 'similarity')"><span>{{ i18n.t("research.similarity", "Similarity") }}</span></label>
                  <label><input type="checkbox" :checked="ragDraft.search_types.includes('lexical')" @change="ragDraft.search_types = ($event.target as HTMLInputElement).checked ? [...new Set([...ragDraft.search_types, 'lexical' as const])] : ragDraft.search_types.filter(item => item !== 'lexical')"><span>{{ i18n.t("settings.route_lexical", "Lexical (BM25)") }}</span></label>
                  <label><input type="checkbox" :checked="ragDraft.search_types.includes('mmr')" @change="ragDraft.search_types = ($event.target as HTMLInputElement).checked ? [...new Set([...ragDraft.search_types, 'mmr' as const])] : ragDraft.search_types.filter(item => item !== 'mmr')"><span>{{ i18n.t("settings.route_mmr", "MMR") }}</span></label>
                </div>
                <p v-if="ragErrors.search_types" class="ui-field-error" role="alert">{{ ragErrors.search_types }}</p>
              </fieldset>
            </div>
            <details class="settings-advanced" :open="advancedOpen" @toggle="advancedOpen = ($event.target as HTMLDetailsElement).open">
              <summary>{{ i18n.t("settings.advanced_retrieval", "Advanced retrieval") }}</summary>
              <div class="config-grid">
                <UiField :label="i18n.t('settings.rag_fetch_k', 'MMR fetch_k')" :hint="i18n.t('settings.rag_fetch_k_help', 'Candidate pool size before diversity ranking. Must be at least retrieval k.')" :error="ragErrors.fetch_k">
                  <input class="control" type="number" min="1" max="5000" v-model.number="ragDraft.fetch_k" :aria-invalid="Boolean(ragErrors.fetch_k)">
                </UiField>
                <UiField :label="i18n.t('settings.rag_lambda', 'MMR lambda')" :hint="i18n.t('settings.rag_lambda_help', '0 favors diversity; 1 favors relevance to the question.')">
                  <input class="control" type="number" min="0" max="1" step="0.05" v-model.number="ragDraft.lambda_mult">
                </UiField>
                <UiField :label="i18n.t('settings.rag_rrf_k', 'RRF k')" :hint="i18n.t('settings.rag_rrf_k_help', 'Smoothing constant for reciprocal-rank fusion. 60 is a common default.')">
                  <input class="control" type="number" min="1" v-model.number="ragDraft.rrf_k">
                </UiField>
                <UiField :label="i18n.t('settings.rag_cross_encoder', 'Cross-encoder model')">
                  <input class="control" v-model="ragDraft.cross_encoder_model">
                </UiField>
                <UiField :label="i18n.t('settings.rag_decompose', 'Query-decomposition max tokens')" :hint="i18n.t('settings.rag_decompose_help', 'Upper bound for the optional query-split step before retrieval.')">
                  <input class="control" type="number" min="64" v-model.number="ragDraft.query_decomposition_num_predict">
                </UiField>
              </div>
            </details>
            <template #actions>
              <UiButton variant="primary" :label="i18n.t('settings.save_rag', 'Save RAG defaults')" @click="saveRag" />
              <UiButton :label="i18n.t('settings.reset_rag', 'Reset retrieval defaults')" @click="resetRag" />
              <UiButton icon="spark" :label="i18n.t('nav.rag', 'Research')" @click="go('/rag', 'rag')" />
            </template>
          </SettingsSection>
        </div>

        <div v-if="isAdmin" v-show="section === 'security'" id="settings-section-security" role="tabpanel" aria-labelledby="settings-nav-security">
          <SettingsSection section-id="security" :title="i18n.t('settings.security_title', 'Security, users, and permissions')" :description="i18n.t('settings.security_help', 'Accounts and role capabilities are enforced by the API, not only this page.')" :persistence="persistKind('link')" status="readonly" :status-label="statusLabel('readonly')">
            <p class="note">{{ i18n.t("roles.users_link_help", "Role capabilities are configured centrally and enforced by both navigation and API permissions.") }}</p>
            <template #actions>
              <UiButton icon="users" :label="i18n.t('nav.users', 'Users')" @click="go('/users')" />
              <UiButton icon="roles" :label="i18n.t('nav.roles', 'Roles & permissions')" @click="go('/roles')" />
            </template>
          </SettingsSection>
        </div>

        <div v-if="isAdmin" v-show="section === 'system'" id="settings-section-system" role="tabpanel" aria-labelledby="settings-nav-system">
          <SettingsSection section-id="backup" :title="i18n.t('settings.backup', 'Backup and restore')" :description="i18n.t('settings.backup_help', 'One portable archive of the browser workspace, loaded records, configuration, the current PDF, and Chroma collections with stored vectors.')" :persistence="persistKind('browser')">
            <p class="info warn">{{ i18n.t("settings.backup_keys_warning", "This full backup can contain provider API keys. Store the ZIP securely. Installed model files are not copied.") }}</p>
            <p class="backup-summary">
              <span><b>{{ backupCounts.files.toLocaleString(i18n.locale) }}</b> {{ i18n.t("settings.jsonl_tabs", "JSONL tabs") }}</span>
              <span><b>{{ backupCounts.jobs.toLocaleString(i18n.locale) }}</b> {{ i18n.t("settings.active_jobs", "active operations") }}</span>
            </p>
            <input ref="restoreInput" type="file" accept=".zip,application/zip" hidden @change="onRestoreFile">
            <template #actions>
              <UiButton variant="primary" icon="download" :label="i18n.t('settings.download_backup', 'Download full backup')" @click="openBackup" />
              <UiButton icon="upload" :label="i18n.t('settings.restore_backup', 'Load from backup')" @click="openRestore" />
            </template>
          </SettingsSection>
          <SettingsSection section-id="viewer" :title="i18n.t('settings.viewer_title', 'Viewer configuration')" :description="i18n.t('settings.viewer_help', 'Reset UI choices or remove audit history without deleting records.')" :persistence="persistKind('browser')">
            <UiField :label="i18n.t('settings.desktop_notifications', 'Desktop notifications')" :hint="i18n.t('settings.notifications_help', 'Browser permission is required. Notifications are local to this browser.')">
              <select id="settings-field-notifications" class="control" :value="notificationsOn ? 'on' : 'off'" @change="notificationsOn = ($event.target as HTMLSelectElement).value === 'on'; saveNotifications()">
                <option value="off">{{ i18n.t("settings.notifications_off", "Off") }}</option>
                <option value="on">{{ i18n.t("settings.notifications_on", "On when background operations finish") }}</option>
              </select>
            </UiField>
            <template #actions>
              <UiButton :label="i18n.t('settings.request_notifications', 'Request notification permission')" @click="requestNotifications" />
              <UiButton :label="i18n.t('settings.reset_columns', 'Reset table columns')" @click="resetColumns" />
              <UiButton :label="i18n.t('settings.expand_panels', 'Expand all UI panels')" @click="expandPanels" />
              <UiButton :label="i18n.t('settings.expand_sidebar', 'Expand navigation sidebar')" @click="expandSidebar" />
              <UiButton :label="i18n.t('settings.restore_upsert', 'Restore removed upsert-queue items')" @click="clearUpsertSuppressions" />
              <UiButton variant="danger" icon="history" :label="i18n.t('settings.clear_updates', 'Clear all record updates')" @click="openUpdates" />
              <UiButton icon="dashboard" :label="i18n.t('nav.home', 'Home')" @click="go('/', 'home')" />
            </template>
          </SettingsSection>
          <SettingsSection section-id="nuke" :title="i18n.t('config.nuke.title', 'Start from scratch')" :description="i18n.t('config.nuke.help', 'Deletes accounts, corpora, PDF builds, vector collections, provider profiles, annotations, job history, and this browser workspace so the next load is a first-run setup. Installed model files are not deleted.')" :persistence="persistKind('backend')" status="readonly">
            <p class="info error">{{ i18n.t("config.nuke.irreversible", "This cannot be undone unless you have a full backup.") }}</p>
            <UiField :label="i18n.t('config.nuke.type_to_enable', 'Type NUKE to enable')" :hint="i18n.t('config.nuke.type_to_enable_help', 'Type NUKE exactly to enable this destructive action.')">
              <input id="settings-field-nuke" class="control" v-model="nukePhrase" autocomplete="off">
            </UiField>
            <template #actions>
              <UiButton variant="danger" :label="i18n.t('config.nuke.button', 'NUKE DerridAI workspace')" :disabled="nukePhrase !== 'NUKE'" :disabled-reason="i18n.t('config.nuke.type_to_enable_help', 'Type NUKE exactly to enable this destructive action.')" @click="openNuke" />
            </template>
          </SettingsSection>
        </div>
      </div>
    </div>

    <UiDialog
      v-if="confirm"
      :open="Boolean(confirm)"
      :title="confirm.title"
      :description="confirm.message"
      :close-label="i18n.t('common.close', 'Close')"
      size="medium"
      @close="closeConfirm"
    >
      <p>{{ confirm.message }}</p>
      <template #footer>
        <UiButton :label="i18n.t('common.cancel', 'Cancel')" :disabled="Boolean(busy)" @click="closeConfirm" />
        <UiButton
          :variant="confirm.kind === 'backup' ? 'primary' : 'danger'"
          :label="busy ? i18n.t('ui.working', 'Working…') : (confirm.kind === 'nuke' ? i18n.t('config.nuke.confirm_label', 'Delete everything') : i18n.t('common.yes', 'Yes'))"
          :disabled="Boolean(busy)"
          @click="applyConfirm"
        />
      </template>
    </UiDialog>
  </main>
</template>

<style scoped>
.settings-page{display:grid;gap:18px;max-width:1280px}
.settings-hero{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;flex-wrap:wrap}
.settings-hero h1{margin:0;font-family:Georgia,"Times New Roman",serif;font-size:clamp(1.6rem,3vw,2.1rem);line-height:1.15}
.settings-hero p{margin:6px 0 0;max-width:68ch;color:var(--muted);line-height:1.5}
.settings-kicker{margin:0;font-size:.8125rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--accent-fg)}
.settings-toolbar{display:grid;gap:8px}
.settings-contents-toggle{display:none}
.settings-layout{display:grid;grid-template-columns:minmax(196px,240px) minmax(0,1fr);gap:20px;align-items:start}
.settings-rail{position:sticky;top:12px}
.settings-pane{display:grid;gap:16px;min-width:0}
.settings-locale-row{display:flex;align-items:center;gap:10px}
.settings-locale-row .control{flex:1}
.theme-choice-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:0;padding:0;border:0}
.theme-choice-grid legend{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}
.theme-choice{display:grid;grid-template-columns:54px minmax(0,1fr);gap:9px;align-items:center;min-height:44px;padding:10px;border:1px solid var(--line);border-radius:10px;background:var(--panel);cursor:pointer}
.theme-choice.selected{background:var(--accent-soft);border-color:var(--accent)}
.theme-choice input{position:absolute;opacity:0}
.theme-choice b{display:block;font-size:.8125rem}
.theme-choice small{display:block;margin-top:3px;color:var(--muted);font-size:.8125rem}
.providers-summary{list-style:none;margin:0;padding:0;display:grid;gap:10px}
.providers-summary li{display:grid;gap:4px;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--panel-2)}
.providers-summary span,.providers-summary small{color:var(--muted);font-size:.8125rem}
.settings-advanced{border:1px solid var(--line);border-radius:12px;padding:8px 12px;background:var(--panel-2)}
.settings-advanced summary{min-height:40px;display:flex;align-items:center;cursor:pointer;font-weight:750}
.settings-advanced .config-grid{margin-top:10px}
.backup-summary{display:flex;flex-wrap:wrap;gap:12px;margin:0;color:var(--muted)}
.field-full{grid-column:1/-1}
.ui-field-error{color:var(--danger);font-size:.8125rem;font-weight:700}
@media (max-width:900px){
  .settings-layout{grid-template-columns:1fr}
  .settings-rail{position:static;display:none}
  .settings-rail.open{display:block}
  .settings-contents-toggle{display:inline-flex}
  .theme-choice-grid{grid-template-columns:1fr}
}
@media (max-width:640px){
  .config-grid{grid-template-columns:1fr}
}
@media (prefers-reduced-motion: reduce){
  .settings-page *{transition:none !important}
}
</style>
