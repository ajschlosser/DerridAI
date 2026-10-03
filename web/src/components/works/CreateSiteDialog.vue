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
import { computed, nextTick, onMounted, ref } from "vue";
import { useI18nStore } from "../../stores/i18n";
import type { LanguageInfo } from "../../api/system";
import type {
  SiteBrowserEmbeddingProfile,
  SiteExportFormat,
  SiteRecordProfile,
  SiteTransformersRuntime,
  SiteVectorStrategy,
} from "../../api/sites";
import type { WorksScopeItem } from "../../types/works";
import AppIcon from "../AppIcon.vue";
import SiteRadioOption from "./SiteRadioOption.vue";

export interface TransformersDownloadProgress {
  file: string;
  received: number;
  total: number;
}

const props = defineProps<{
  works: WorksScopeItem[];
  storeName: string;
  initialWork?: string;
  languages: LanguageInfo[];
  transformersRuntime?: SiteTransformersRuntime;
  browserEmbeddingProfile?: SiteBrowserEmbeddingProfile;
  downloadProgress?: TransformersDownloadProgress | null;
  busy?: boolean;
  error?: string;
}>();

const emit = defineEmits<{
  cancel: [];
  "delete-runtime": [];
  "download-runtime": [];
  create: [
    payload: {
      title: string;
      description: string;
      works: string[];
      languages: string[];
      include_transformers: boolean;
      vector_strategy: SiteVectorStrategy;
      export_format: SiteExportFormat;
      record_profile: SiteRecordProfile;
      provider_proxy_upstream: string | null;
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
const vectorStrategy = ref<SiteVectorStrategy>("browser-default");
const providerProxyEnabled = ref(false);
const providerProxyUpstream = ref("http://localhost:11434/v1");
const selectedLanguages = ref<string[]>(props.languages.map((item) => item.code));

const selectedCount = computed(() => selected.value.length);
const providerProxyValid = computed(() => {
  if (exportFormat.value !== "nginx-docker" || !providerProxyEnabled.value) return true;
  try {
    const parsed = new URL(providerProxyUpstream.value.trim());
    return (
      ["http:", "https:"].includes(parsed.protocol) &&
      Boolean(parsed.hostname) &&
      !parsed.username &&
      !parsed.password &&
      !parsed.search &&
      !parsed.hash
    );
  } catch {
    return false;
  }
});
const canCreate = computed(() =>
  Boolean(
    selectedCount.value &&
      selectedLanguages.value.length &&
      props.storeName &&
      !props.busy &&
      providerProxyValid.value,
  ),
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

function formatMegabytes(bytes: number): string {
  return (bytes / (1024 * 1024)).toFixed(1);
}

function submit() {
  if (!canCreate.value) return;
  emit("create", {
    title: title.value.trim() || selected.value[0] || "",
    description: description.value.trim(),
    works: [...selected.value],
    languages: [...selectedLanguages.value],
    include_transformers: true,
    vector_strategy: vectorStrategy.value,
    export_format: exportFormat.value,
    record_profile: recordProfile.value,
    provider_proxy_upstream:
      exportFormat.value === "nginx-docker" && providerProxyEnabled.value
        ? providerProxyUpstream.value.trim()
        : null,
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
        <section class="publication-section create-site-fields">
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

        <section class="publication-section" aria-labelledby="site-content-heading">
          <div class="publication-section-head">
            <div>
              <h3 id="site-content-heading">{{ i18n.t("site.create_content") }}</h3>
              <p>{{ i18n.t("site.create_content_help") }}</p>
            </div>
          </div>
          <div class="publication-content-grid">
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
          </div>
        </section>

        <section class="publication-section" aria-labelledby="site-search-data-heading">
          <div class="publication-section-head">
            <div>
              <h3 id="site-search-data-heading">{{ i18n.t("site.create_search_data") }}</h3>
              <p>{{ i18n.t("site.create_search_data_help") }}</p>
            </div>
          </div>
          <div class="publication-settings-grid">
            <fieldset class="site-option-group site-vector-profile">
              <legend>{{ i18n.t("site.create_vectors") }}</legend>
              <p class="site-choice-help">{{ i18n.t("site.create_vectors_help") }}</p>
              <SiteRadioOption
                v-model="vectorStrategy"
                name="site-vector-profile"
                value="browser-default"
                :title="i18n.t('site.create_vectors_recommended')"
                :description="i18n.t('site.create_vectors_recommended_help')"
                :badge="i18n.t('site.create_recommended')"
              />
              <p v-if="props.browserEmbeddingProfile" class="site-model-note">
                {{
                  i18n.tf("site.create_vectors_model_summary", {
                    model: props.browserEmbeddingProfile.model,
                    dimension: props.browserEmbeddingProfile.dimension,
                    size: formatMegabytes(props.browserEmbeddingProfile.download_bytes),
                  })
                }}
              </p>
              <SiteRadioOption
                v-model="vectorStrategy"
                name="site-vector-profile"
                value="source"
                :title="i18n.t('site.create_vectors_include')"
                :description="i18n.t('site.create_vectors_include_help')"
              />
              <SiteRadioOption
                v-model="vectorStrategy"
                name="site-vector-profile"
                value="browser"
                :title="i18n.t('site.create_vectors_browser')"
                :description="i18n.t('site.create_vectors_browser_help')"
              />
            </fieldset>

            <fieldset class="site-option-group site-record-profile">
              <legend>{{ i18n.t("site.create_record_profile") }}</legend>
              <p class="site-choice-help">{{ i18n.t("site.create_record_profile_help") }}</p>
              <SiteRadioOption
                v-model="recordProfile"
                name="site-record-profile"
                value="complete"
                :title="i18n.t('site.create_profile_complete')"
                :description="i18n.t('site.create_profile_complete_help')"
              />
              <small class="site-celf-status" data-celf="complete">
                {{ i18n.t("site.create_profile_complete_celf") }}
              </small>
              <SiteRadioOption
                v-model="recordProfile"
                name="site-record-profile"
                value="reader"
                :title="i18n.t('site.create_profile_reader')"
                :description="i18n.t('site.create_profile_reader_help')"
              />
              <small class="site-celf-status" data-celf="reader">
                {{ i18n.t("site.create_profile_reader_celf") }}
              </small>
            </fieldset>
          </div>
        </section>

        <section class="publication-section" aria-labelledby="site-delivery-heading">
          <div class="publication-section-head">
            <div>
              <h3 id="site-delivery-heading">{{ i18n.t("site.create_delivery") }}</h3>
              <p>{{ i18n.t("site.create_delivery_help") }}</p>
            </div>
          </div>
          <fieldset class="site-option-group site-export-format">
            <legend class="sr-only">{{ i18n.t("site.create_export_format") }}</legend>
            <div class="site-format-grid">
              <SiteRadioOption
                v-model="exportFormat"
                name="site-export-format"
                value="two-file"
                :title="i18n.t('site.create_format_two_file')"
                :description="i18n.t('site.create_format_two_file_help')"
              />
              <SiteRadioOption
                v-model="exportFormat"
                name="site-export-format"
                value="local-single-file"
                :title="i18n.t('site.create_format_local')"
                :description="i18n.t('site.create_format_local_help')"
              />
              <SiteRadioOption
                v-model="exportFormat"
                name="site-export-format"
                value="nginx-docker"
                :title="i18n.t('site.create_format_nginx')"
                :description="i18n.t('site.create_format_nginx_help')"
              />
            </div>
          </fieldset>
        </section>

        <details class="publication-advanced">
          <summary>{{ i18n.t("site.create_advanced") }}</summary>
          <div class="publication-advanced-body">
            <fieldset
              v-if="exportFormat === 'nginx-docker'"
              class="site-option-group site-provider-proxy"
              data-site-provider-proxy
            >
              <legend>{{ i18n.t("site.create_provider_proxy") }}</legend>
              <p class="site-choice-help">{{ i18n.t("site.create_provider_proxy_help") }}</p>
              <label class="site-check-option">
                <input
                  v-model="providerProxyEnabled"
                  type="checkbox"
                  data-site-provider-proxy-enabled
                />
                <span>
                  <strong>{{ i18n.t("site.create_provider_proxy_enable") }}</strong>
                  <small>{{ i18n.t("site.create_provider_proxy_enable_help") }}</small>
                </span>
              </label>
              <label v-if="providerProxyEnabled" class="field">
                <span>{{ i18n.t("site.create_provider_proxy_upstream") }}</span>
                <input
                  v-model="providerProxyUpstream"
                  class="control"
                  type="url"
                  autocomplete="url"
                  maxlength="2048"
                  data-site-provider-proxy-upstream
                  :aria-invalid="providerProxyValid ? undefined : 'true'"
                  :placeholder="i18n.t('site.create_provider_proxy_upstream_placeholder')"
                />
                <small>{{ i18n.t("site.create_provider_proxy_upstream_help") }}</small>
              </label>
              <p
                v-if="providerProxyEnabled && !providerProxyValid"
                class="site-create-error"
                role="alert"
              >
                {{ i18n.t("site.create_provider_proxy_invalid") }}
              </p>
              <p v-if="providerProxyEnabled" class="site-choice-help">
                {{ i18n.t("site.create_provider_proxy_security") }}
              </p>
            </fieldset>

            <section class="runtime-section" data-site-transformers>
              <h4>{{ i18n.t("site.create_transformers") }}</h4>
              <p class="site-choice-help">{{ i18n.t("site.create_transformers_help") }}</p>
              <template v-if="props.transformersRuntime">
                <p v-if="exportFormat === 'nginx-docker'" class="site-choice-help">
                  {{ i18n.t("site.create_transformers_help_files") }}
                </p>
                <p v-else class="site-choice-help">
                  {{
                    i18n.tf("site.create_transformers_help_inline", {
                      size: formatMegabytes(props.transformersRuntime.inline_bytes),
                    })
                  }}
                </p>
                <p data-transformers-source>
                  {{
                    props.transformersRuntime.cached
                      ? i18n.t("site.create_transformers_cached")
                      : i18n.tf("site.create_transformers_download", {
                          size: formatMegabytes(props.transformersRuntime.download_bytes),
                        })
                  }}
                </p>
                <progress
                  v-if="props.downloadProgress"
                  :value="props.downloadProgress.received"
                  :max="Math.max(props.downloadProgress.total, 1)"
                  :aria-label="i18n.t('site.create_transformers_downloading')"
                />
                <p v-if="props.downloadProgress" role="status">
                  {{
                    i18n.tf("site.create_transformers_progress", {
                      file: props.downloadProgress.file || "Transformers.js",
                      received: formatMegabytes(props.downloadProgress.received),
                      total: formatMegabytes(props.downloadProgress.total),
                    })
                  }}
                </p>
                <div class="runtime-actions">
                  <button
                    v-if="props.transformersRuntime.cached"
                    type="button"
                    class="btn small"
                    data-transformers-delete
                    :disabled="props.busy"
                    @click="emit('delete-runtime')"
                  >
                    {{ i18n.t("site.create_transformers_delete") }}
                  </button>
                  <button
                    v-else
                    type="button"
                    class="btn small"
                    data-transformers-download
                    :disabled="props.busy"
                    @click="emit('download-runtime')"
                  >
                    {{ i18n.t("site.create_transformers_redownload") }}
                  </button>
                </div>
              </template>
              <p v-else>{{ i18n.t("site.create_transformers_unavailable") }}</p>
            </section>
          </div>
        </details>

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
  width: min(64rem, calc(100vw - 2rem));
  max-height: min(92vh, 58rem);
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
  padding: 1rem 1.2rem;
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
  max-width: 46rem;
  margin: 0.4rem 0 0;
  color: var(--muted);
  line-height: 1.5;
}

.create-site-body {
  display: grid;
  gap: 1.15rem;
  padding: 1.15rem 1.2rem 1.4rem;
  overflow: auto;
}

.publication-section {
  min-width: 0;
}

.publication-section + .publication-section {
  padding-top: 1.15rem;
  border-top: 1px solid var(--border-subtle);
}

.publication-section-head {
  display: flex;
  gap: 1rem;
  align-items: start;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.publication-section-head h3 {
  margin: 0;
  font-size: 1rem;
}

.publication-section-head p {
  max-width: 62ch;
  margin: 0.25rem 0 0;
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1.45;
}

.create-site-fields {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(17rem, 0.7fr);
  gap: 0.8rem;
}

.create-site-fields .field:first-child,
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
  gap: 0.3rem;
  padding: 0.85rem;
  border-left: 3px solid var(--ui-accent);
  background: var(--surface-raised);
}

.site-store-summary > span,
.site-feature-summary strong {
  font-size: 0.8rem;
  font-weight: 800;
}

.site-store-summary small,
.site-feature-summary small,
.site-work-option small {
  color: var(--muted);
  line-height: 1.45;
}

.publication-content-grid,
.publication-settings-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(17rem, 0.8fr);
  gap: 1rem;
  align-items: start;
}

.site-work-picker,
.site-choice-picker,
.site-option-group {
  min-width: 0;
  margin: 0;
  padding: 0;
  border: 0;
}

.site-work-picker legend,
.site-choice-picker legend,
.site-option-group legend {
  padding: 0;
  margin-bottom: 0.5rem;
  font-weight: 800;
}

.site-choice-help {
  margin: 0 0 0.65rem;
  color: var(--muted);
  font-size: 0.88rem;
  line-height: 1.45;
}

.site-option-group {
  display: grid;
  gap: 0.5rem;
}

.site-model-note,
.site-celf-status {
  display: block;
  margin: 0 0 0.2rem 1.75rem;
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.4;
}

.site-format-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.55rem;
}

.site-work-picker-toolbar {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.55rem;
  color: var(--muted);
  font-size: 0.82rem;
}

.site-work-picker-toolbar > div,
.runtime-actions {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.site-work-list,
.site-choice-list {
  display: grid;
  max-height: 16rem;
  gap: 0.25rem;
  overflow: auto;
  padding-right: 0.2rem;
}

.site-work-option {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.6rem;
  align-items: start;
  padding: 0.55rem;
  border-radius: 7px;
}

.site-work-option:hover {
  background: var(--surface-raised);
}

.site-work-option:focus-within {
  outline: 2px solid var(--ui-accent);
  outline-offset: 1px;
}

.site-work-option input {
  width: 1rem;
  height: 1rem;
  margin-top: 0.2rem;
}

.site-work-option span {
  display: grid;
  min-width: 0;
  gap: 0.12rem;
}

.site-check-option {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.65rem;
  align-items: start;
}

.site-check-option span {
  display: grid;
  gap: 0.15rem;
}

.site-check-option small {
  color: var(--muted);
}

.publication-advanced {
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}

.publication-advanced > summary {
  padding: 0.8rem 0;
  font-weight: 800;
  cursor: pointer;
}

.publication-advanced-body {
  display: grid;
  gap: 1rem;
  padding: 0 0 1rem;
}

.runtime-section {
  display: grid;
  gap: 0.45rem;
}

.runtime-section h4 {
  margin: 0;
  font-size: 0.95rem;
}

.runtime-section p {
  margin-top: 0;
}

.site-feature-summary {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.7rem;
  align-items: start;
  padding: 0.85rem;
  border-radius: 8px;
  background: color-mix(in srgb, var(--ui-accent) 6%, var(--surface-raised));
}

.site-feature-summary > svg {
  width: 1.1rem;
  margin-top: 0.12rem;
}

.site-feature-summary span {
  display: grid;
  gap: 0.15rem;
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

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 800px) {
  .create-site-fields,
  .publication-content-grid,
  .publication-settings-grid,
  .site-format-grid {
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
