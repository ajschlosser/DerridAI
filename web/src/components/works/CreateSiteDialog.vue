<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { useI18nStore } from "../../stores/i18n";
import type { LanguageInfo, ProviderProfile } from "../../api/system";
import type { SiteExportFormat, SiteRecordProfile } from "../../api/sites";
import type { WorksScopeItem } from "../../types/works";
import AppIcon from "../AppIcon.vue";

const props = defineProps<{
  works: WorksScopeItem[];
  storeName: string;
  initialWork?: string;
  languages: LanguageInfo[];
  providerProfiles: ProviderProfile[];
  busy?: boolean;
  error?: string;
}>();

const emit = defineEmits<{
  cancel: [];
  create: [
    payload: {
      title: string;
      description: string;
      works: string[];
      languages: string[];
      provider_profile_ids: string[];
      export_format: SiteExportFormat;
      record_profile: SiteRecordProfile;
    },
  ];
}>();

const i18n = useI18nStore();
const dialog = ref<HTMLDialogElement | null>(null);
const selected = ref<string[]>(props.initialWork ? [props.initialWork] : []);
const title = ref(props.initialWork || "");
const description = ref("");
const exportFormat = ref<SiteExportFormat>("two-file");
const recordProfile = ref<SiteRecordProfile>("complete");
const selectedLanguages = ref<string[]>(props.languages.map((item) => item.code));
const selectedProviderProfiles = ref<string[]>(props.providerProfiles.map((item) => item.id));

const selectedCount = computed(() => selected.value.length);
const canCreate = computed(() =>
  Boolean(selectedCount.value && selectedLanguages.value.length && props.storeName && !props.busy),
);

function toggle(work: string, checked: boolean) {
  selected.value = checked
    ? [...new Set([...selected.value, work])]
    : selected.value.filter((item) => item !== work);
  if (!title.value.trim() && selected.value.length === 1) title.value = selected.value[0] || "";
}

function selectAll() {
  selected.value = props.works.map((item) => item.work);
}

function clearSelection() {
  selected.value = [];
}

function toggleLanguage(code: string, checked: boolean) {
  selectedLanguages.value = checked
    ? [...new Set([...selectedLanguages.value, code])]
    : selectedLanguages.value.filter((item) => item !== code);
}

function selectAllLanguages() {
  selectedLanguages.value = props.languages.map((item) => item.code);
}

function clearLanguages() {
  selectedLanguages.value = [];
}

function toggleProvider(id: string, checked: boolean) {
  selectedProviderProfiles.value = checked
    ? [...new Set([...selectedProviderProfiles.value, id])]
    : selectedProviderProfiles.value.filter((item) => item !== id);
}

function selectAllProviders() {
  selectedProviderProfiles.value = props.providerProfiles.map((item) => item.id);
}

function clearProviders() {
  selectedProviderProfiles.value = [];
}

function submit() {
  if (!canCreate.value) return;
  emit("create", {
    title: title.value.trim() || selected.value[0] || "",
    description: description.value.trim(),
    works: [...selected.value],
    languages: [...selectedLanguages.value],
    provider_profile_ids: [...selectedProviderProfiles.value],
    export_format: exportFormat.value,
    record_profile: recordProfile.value,
  });
}

onMounted(async () => {
  await nextTick();
  dialog.value?.showModal();
});
</script>

<template>
  <dialog
    ref="dialog"
    class="create-site-dialog"
    aria-labelledby="create-site-title"
    @cancel.prevent="emit('cancel')"
    @close="emit('cancel')"
  >
    <form method="dialog" class="create-site-shell" @submit.prevent="submit">
      <header class="create-site-header">
        <div>
          <span class="section-label">{{ i18n.t("works.workspace_kicker") }}</span>
          <h2 id="create-site-title">{{ i18n.t("site.create_dialog_title") }}</h2>
          <p>{{ i18n.t("site.create_dialog_help") }}</p>
        </div>
        <button
          type="button"
          class="btn icon-button"
          :aria-label="i18n.t('common.close')"
          @click="emit('cancel')"
        >
          <AppIcon name="close" aria-hidden="true" />
        </button>
      </header>

      <div class="create-site-body">
        <section class="create-site-fields" :aria-label="i18n.t('site.create_dialog_title')">
          <label class="field">
            <span>{{ i18n.t("site.create_title") }}</span>
            <input
              v-model="title"
              class="control"
              maxlength="300"
              :placeholder="i18n.t('site.create_title_placeholder')"
            />
          </label>
          <label class="field">
            <span>{{ i18n.t("site.create_description") }}</span>
            <textarea
              v-model="description"
              class="control"
              maxlength="4000"
              rows="3"
              :placeholder="i18n.t('site.create_description_placeholder')"
            />
          </label>
          <div class="site-store-summary">
            <span>{{ i18n.t("site.create_store") }}</span>
            <strong>{{ props.storeName }}</strong>
            <small>{{ i18n.t("site.create_store_help") }}</small>
          </div>
        </section>

        <fieldset class="site-export-format">
          <legend>{{ i18n.t("site.create_export_format") }}</legend>
          <label class="site-export-option">
            <input v-model="exportFormat" type="radio" value="two-file" />
            <span>
              <strong>{{ i18n.t("site.create_format_two_file") }}</strong>
              <small>{{ i18n.t("site.create_format_two_file_help") }}</small>
            </span>
          </label>
          <label class="site-export-option">
            <input v-model="exportFormat" type="radio" value="local-single-file" />
            <span>
              <strong>{{ i18n.t("site.create_format_local") }}</strong>
              <small>{{ i18n.t("site.create_format_local_help") }}</small>
            </span>
          </label>
          <label class="site-export-option">
            <input v-model="exportFormat" type="radio" value="nginx-docker" />
            <span>
              <strong>{{ i18n.t("site.create_format_nginx") }}</strong>
              <small>{{ i18n.t("site.create_format_nginx_help") }}</small>
            </span>
          </label>
        </fieldset>

        <fieldset class="site-export-format site-record-profile">
          <legend>{{ i18n.t("site.create_record_profile") }}</legend>
          <p class="site-choice-help">{{ i18n.t("site.create_record_profile_help") }}</p>
          <label class="site-export-option">
            <input
              v-model="recordProfile"
              type="radio"
              name="site-record-profile"
              value="complete"
            />
            <span>
              <strong>{{ i18n.t("site.create_profile_complete") }}</strong>
              <small>{{ i18n.t("site.create_profile_complete_help") }}</small>
              <small class="site-celf-status" data-celf="complete">
                {{ i18n.t("site.create_profile_complete_celf") }}
              </small>
            </span>
          </label>
          <label class="site-export-option">
            <input v-model="recordProfile" type="radio" name="site-record-profile" value="reader" />
            <span>
              <strong>{{ i18n.t("site.create_profile_reader") }}</strong>
              <small>{{ i18n.t("site.create_profile_reader_help") }}</small>
              <small class="site-celf-status" data-celf="reader">
                {{ i18n.t("site.create_profile_reader_celf") }}
              </small>
            </span>
          </label>
        </fieldset>

        <fieldset class="site-choice-picker">
          <legend>{{ i18n.t("site.create_languages") }}</legend>
          <p class="site-choice-help">{{ i18n.t("site.create_languages_help") }}</p>
          <div class="site-work-picker-toolbar">
            <span>
              {{ i18n.tf("site.create_languages_selected", { count: selectedLanguages.length }) }}
            </span>
            <div>
              <button type="button" class="btn small" @click="selectAllLanguages">
                {{ i18n.t("site.create_select_all") }}
              </button>
              <button type="button" class="btn small" @click="clearLanguages">
                {{ i18n.t("site.create_clear") }}
              </button>
            </div>
          </div>
          <div class="site-choice-list">
            <label
              v-for="language in props.languages"
              :key="language.code"
              class="site-work-option"
            >
              <input
                type="checkbox"
                :checked="selectedLanguages.includes(language.code)"
                :data-site-language="language.code"
                @change="toggleLanguage(language.code, ($event.target as HTMLInputElement).checked)"
              />
              <span>
                <strong>{{ language.flag }} {{ language.name }}</strong>
                <small>{{ language.code }}</small>
              </span>
            </label>
          </div>
          <p v-if="!selectedLanguages.length" class="site-create-error" role="alert">
            {{ i18n.t("site.create_language_required") }}
          </p>
        </fieldset>

        <fieldset class="site-choice-picker">
          <legend>{{ i18n.t("site.create_provider_profiles") }}</legend>
          <p class="site-choice-help">{{ i18n.t("site.create_provider_profiles_help") }}</p>
          <div v-if="props.providerProfiles.length" class="site-work-picker-toolbar">
            <span>
              {{
                i18n.tf("site.create_providers_selected", {
                  count: selectedProviderProfiles.length,
                })
              }}
            </span>
            <div>
              <button type="button" class="btn small" @click="selectAllProviders">
                {{ i18n.t("site.create_select_all") }}
              </button>
              <button type="button" class="btn small" @click="clearProviders">
                {{ i18n.t("site.create_clear") }}
              </button>
            </div>
          </div>
          <div v-if="props.providerProfiles.length" class="site-choice-list">
            <label
              v-for="profile in props.providerProfiles"
              :key="profile.id"
              class="site-work-option"
            >
              <input
                type="checkbox"
                :checked="selectedProviderProfiles.includes(profile.id)"
                :data-site-provider="profile.id"
                @change="toggleProvider(profile.id, ($event.target as HTMLInputElement).checked)"
              />
              <span>
                <strong>{{ profile.name || profile.id }}</strong>
                <small>
                  {{
                    profile.type === "openai"
                      ? i18n.t("site.create_provider_openai")
                      : i18n.t("site.create_provider_ollama")
                  }}
                  <template v-if="profile.model"> · {{ profile.model }}</template>
                </small>
              </span>
            </label>
          </div>
          <p v-else class="site-choice-help">{{ i18n.t("site.create_no_provider_profiles") }}</p>
        </fieldset>

        <fieldset class="site-work-picker">
          <legend>{{ i18n.t("site.create_select_works") }}</legend>
          <div class="site-work-picker-toolbar">
            <span>{{ i18n.tf("site.create_selected_count", { count: selectedCount }) }}</span>
            <div>
              <button type="button" class="btn small" @click="selectAll">
                {{ i18n.t("site.create_select_all") }}
              </button>
              <button type="button" class="btn small" @click="clearSelection">
                {{ i18n.t("site.create_clear") }}
              </button>
            </div>
          </div>
          <div class="site-work-list">
            <label v-for="work in props.works" :key="work.work" class="site-work-option">
              <input
                type="checkbox"
                :checked="selected.includes(work.work)"
                :data-site-work="work.work"
                @change="toggle(work.work, ($event.target as HTMLInputElement).checked)"
              />
              <span>
                <strong>{{ work.work }}</strong>
                <small>
                  {{ work.authors.join(", ") }}
                  <template v-if="work.year_label"> · {{ work.year_label }}</template>
                  · {{ work.count.toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.records") }}
                </small>
              </span>
            </label>
          </div>
        </fieldset>

        <aside class="site-feature-summary">
          <AppIcon name="spark" aria-hidden="true" />
          <span>
            <strong>{{ i18n.t("site.create_features_title") }}</strong>
            <small>{{ i18n.t("site.create_features_help") }}</small>
          </span>
        </aside>

        <p v-if="props.error" class="site-create-error" role="alert">{{ props.error }}</p>
      </div>

      <footer class="create-site-actions">
        <button type="button" class="btn" :disabled="props.busy" @click="emit('cancel')">
          {{ i18n.t("common.cancel") }}
        </button>
        <button type="submit" class="btn primary" :disabled="!canCreate">
          <AppIcon name="download" aria-hidden="true" />
          {{
            props.busy
              ? i18n.t("site.create_busy")
              : exportFormat === "two-file"
                ? i18n.t("site.create_action_two_file")
                : exportFormat === "local-single-file"
                  ? i18n.t("site.create_action_local")
                  : i18n.t("site.create_action_nginx")
          }}
        </button>
      </footer>
    </form>
  </dialog>
</template>

<style scoped>
.create-site-dialog {
  width: min(58rem, calc(100vw - 2rem));
  max-height: min(90vh, 52rem);
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface-card);
  color: var(--text);
  box-shadow: var(--shadow-overlay);
}

.create-site-dialog::backdrop {
  background: color-mix(in srgb, var(--text) 38%, transparent);
}

.create-site-shell {
  display: grid;
  max-height: inherit;
  grid-template-rows: auto minmax(0, 1fr) auto;
}

.create-site-header,
.create-site-actions {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  justify-content: space-between;
  padding: 1rem 1.15rem;
  background: var(--surface-raised);
}

.create-site-header {
  border-bottom: 1px solid var(--border);
}

.create-site-header h2 {
  margin: 0.2rem 0 0;
  font-size: 1.45rem;
}

.create-site-header p {
  max-width: 44rem;
  margin: 0.45rem 0 0;
  color: var(--muted);
  line-height: 1.5;
}

.create-site-body {
  display: grid;
  gap: 1rem;
  padding: 1rem 1.15rem;
  overflow: auto;
}

.create-site-fields {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(16rem, 0.75fr);
  gap: 0.8rem;
}

.create-site-fields .field:first-child {
  grid-column: 1;
}

.create-site-fields .field:nth-child(2) {
  grid-column: 1;
}

.create-site-fields textarea {
  resize: vertical;
}

.site-store-summary {
  grid-column: 2;
  grid-row: 1 / span 2;
  display: grid;
  align-content: start;
  gap: 0.35rem;
  padding: 0.85rem;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface-raised);
}

.site-store-summary > span,
.site-feature-summary strong {
  font-size: 0.82rem;
  font-weight: 800;
}

.site-store-summary small,
.site-feature-summary small,
.site-work-option small {
  color: var(--muted);
  line-height: 1.45;
}

.site-export-format {
  display: grid;
  min-width: 0;
  gap: 0.5rem;
  margin: 0;
  padding: 0.85rem;
  border: 1px solid var(--border);
  border-radius: 10px;
}

.site-export-format legend {
  padding: 0 0.35rem;
  font-weight: 800;
}

.site-export-option {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.7rem;
  align-items: start;
  padding: 0.75rem;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--surface-raised);
  cursor: pointer;
}

.site-export-option:has(input:checked) {
  border-color: var(--ui-accent);
  box-shadow: 0 0 0 1px var(--ui-accent);
}

.site-export-option input {
  margin-top: 0.2rem;
}

.site-export-option span {
  display: grid;
  gap: 0.2rem;
}

.site-export-option small {
  color: var(--muted);
  line-height: 1.45;
}

.site-export-option .site-celf-status {
  color: var(--text);
  font-weight: 600;
}

.site-work-picker,
.site-choice-picker {
  min-width: 0;
  margin: 0;
  padding: 0.85rem;
  border: 1px solid var(--border);
  border-radius: 10px;
}

.site-work-picker legend,
.site-choice-picker legend {
  padding: 0 0.35rem;
  font-weight: 800;
}

.site-choice-help {
  margin: 0 0 0.65rem;
  color: var(--muted);
  line-height: 1.45;
}

.site-work-picker-toolbar {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.65rem;
  color: var(--muted);
  font-size: 0.84rem;
}

.site-work-picker-toolbar > div {
  display: flex;
  gap: 0.4rem;
}

.site-work-list,
.site-choice-list {
  display: grid;
  max-height: 18rem;
  gap: 0.35rem;
  overflow: auto;
}

.site-work-option {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.65rem;
  align-items: start;
  padding: 0.65rem;
  border-radius: 8px;
}

.site-work-option:hover {
  background: var(--surface-raised);
}

.site-work-option input {
  width: 1rem;
  height: 1rem;
  margin-top: 0.2rem;
}

.site-work-option span {
  display: grid;
  min-width: 0;
  gap: 0.15rem;
}

.site-feature-summary {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.7rem;
  align-items: start;
  padding: 0.85rem;
  border-radius: 10px;
  background: color-mix(in srgb, var(--ui-accent) 7%, var(--surface-raised));
}

.site-feature-summary > svg {
  width: 1.15rem;
  margin-top: 0.15rem;
}

.site-feature-summary span {
  display: grid;
  gap: 0.2rem;
}

.site-create-error {
  margin: 0;
  color: var(--tone-danger-fg);
}

.create-site-actions {
  align-items: center;
  justify-content: flex-end;
  border-top: 1px solid var(--border);
}

@media (max-width: 720px) {
  .create-site-fields {
    grid-template-columns: 1fr;
  }

  .create-site-fields .field,
  .site-store-summary {
    grid-column: 1;
    grid-row: auto;
  }

  .site-work-picker-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
