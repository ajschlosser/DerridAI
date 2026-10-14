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
import { computed, ref, useId } from "vue";
import type { AuthorCandidate, SourceProviderId, SourceProviderInfo } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import { languageName, sortLanguageCodes } from "../../domain/languages";
import type { CaptureIncludes } from "../../domain/captureReview";
import UiCombobox from "../ui/UiCombobox.vue";

/**
 * Libraries, contribution roles and languages for a capture. Languages default to "all"; the
 * choosable list is the Wikisource projects the API discovered, never a list fixed in the browser.
 */
const props = defineProps<{
  providers: SourceProviderId[];
  includes: CaptureIncludes;
  author?: AuthorCandidate | null;
  /** null = every language. */
  languages: string[] | null;
  providerInfo: SourceProviderInfo[];
}>();
const emit = defineEmits<{
  "update:providers": [SourceProviderId[]];
  "update:includes": [CaptureIncludes];
  "update:languages": [string[] | null];
}>();
const i18n = useI18nStore();
const id = useId();

const wikisource = computed(() =>
  props.providerInfo.find((item) => item.provider === "wikisource"),
);
const gutenberg = computed(() => props.providerInfo.find((item) => item.provider === "gutenberg"));
const projectCodes = computed(() =>
  sortLanguageCodes(
    (wikisource.value && "projects" in wikisource.value ? wikisource.value.projects : [])
      .map((project) => project.code)
      .filter((code) => code !== "mul"),
    i18n.locale,
  ),
);
const languageChoices = computed(() =>
  sortLanguageCodes([...(props.author?.languages || []), ...projectCodes.value], i18n.locale),
);
const originalLanguages = computed(() =>
  sortLanguageCodes(props.author?.original_languages || [], i18n.locale),
);
const originalLanguage = computed(() =>
  originalLanguages.value.length === 1 ? originalLanguages.value[0] : "",
);
const languageDraft = ref("");
const languageDisabled = computed(() => false);
const INCLUDES: Array<keyof CaptureIncludes> = [
  "authored",
  "translations",
  "translator",
  "editor",
  "other",
];
const noRole = computed(
  () =>
    !props.includes.authored &&
    !props.includes.translations &&
    !props.includes.translator &&
    !props.includes.editor &&
    !props.includes.other,
);

function toggleProvider(provider: SourceProviderId, on: boolean) {
  const next = new Set(props.providers);
  if (on) next.add(provider);
  else next.delete(provider);
  emit(
    "update:providers",
    (["gutenberg", "wikisource"] as SourceProviderId[]).filter((item) => next.has(item)),
  );
}
function toggleInclude(key: keyof CaptureIncludes, on: boolean) {
  emit("update:includes", { ...props.includes, [key]: on });
  if (key === "translations" && !on) {
    emit("update:languages", originalLanguage.value ? [originalLanguage.value] : []);
  }
}
function toggleLanguage(code: string, on: boolean) {
  const next = new Set(props.languages || []);
  if (on) next.add(code);
  else next.delete(code);
  emit("update:languages", [...next]);
}
function addLanguage() {
  const code = languageDraft.value.trim().toLowerCase().replaceAll("_", "-");
  if (!code) return;
  const next = new Set(props.languages || []);
  next.add(code);
  languageDraft.value = "";
  emit("update:languages", [...next]);
}
function addLanguageValue(value: string) {
  languageDraft.value = value;
  addLanguage();
}
</script>

<template>
  <div class="capture-options">
    <fieldset>
      <legend>{{ i18n.t("capture.options.providers") }}</legend>
      <label v-for="provider in ['gutenberg', 'wikisource'] as SourceProviderId[]" :key="provider">
        <input
          type="checkbox"
          :checked="providers.includes(provider)"
          :data-provider="provider"
          :disabled="
            provider === 'wikisource' &&
            author?.identity_source === 'gutenberg' &&
            !author.wikidata_qid
          "
          @change="toggleProvider(provider, ($event.target as HTMLInputElement).checked)"
        />
        <span>
          <strong>{{ i18n.t(`capture.provider.${provider}`) }}</strong>
          <small v-if="provider === 'gutenberg'">{{
            gutenberg && "catalogue_ready" in gutenberg && gutenberg.catalogue_ready
              ? i18n.t("capture.options.gutenberg_catalogue_ready")
              : i18n.t("capture.options.gutenberg_catalogue_missing")
          }}</small>
          <small v-else>{{
            i18n.tf("capture.options.wikisource_projects", { count: projectCodes.length })
          }}</small>
        </span>
      </label>
      <p v-if="!providers.length" class="co-invalid" role="alert">
        {{ i18n.t("capture.options.need_provider") }}
      </p>
    </fieldset>

    <fieldset>
      <legend>{{ i18n.t("capture.options.include") }}</legend>
      <label v-for="key in INCLUDES" :key="key" :class="{ nested: key === 'translations' }">
        <input
          type="checkbox"
          :checked="includes[key]"
          :data-include="key"
          @change="toggleInclude(key, ($event.target as HTMLInputElement).checked)"
        />
        <span>
          <strong>{{ i18n.t(`capture.options.include_${key}`) }}</strong>
          <small>{{ i18n.t(`capture.options.include_${key}_help`) }}</small>
        </span>
      </label>
      <p v-if="noRole" class="co-invalid" role="alert">
        {{ i18n.t("capture.options.need_role") }}
      </p>
    </fieldset>

    <fieldset>
      <legend>{{ i18n.t("capture.options.languages") }}</legend>
      <label>
        <input
          type="radio"
          :name="`${id}-languages`"
          :checked="languages === null"
          :disabled="languageDisabled"
          data-languages="all"
          @change="emit('update:languages', null)"
        />
        <span
          ><strong>{{ i18n.t("capture.options.languages_all") }}</strong></span
        >
      </label>
      <label>
        <input
          type="radio"
          :name="`${id}-languages`"
          :checked="languages !== null"
          :disabled="languageDisabled"
          data-languages="some"
          @change="emit('update:languages', [])"
        />
        <span
          ><strong>{{ i18n.t("capture.options.languages_some") }}</strong></span
        >
      </label>
      <div
        v-if="languages !== null"
        class="co-languages"
        role="group"
        :aria-label="i18n.t('capture.options.languages_some')"
      >
        <label v-for="code in languageChoices" :key="code">
          <input
            type="checkbox"
            :checked="languages.includes(code)"
            :disabled="languageDisabled"
            :data-language="code"
            @change="toggleLanguage(code, ($event.target as HTMLInputElement).checked)"
          />
          <span>{{ languageName(code, i18n.locale) }}</span>
        </label>
        <div class="co-language-add">
          <UiCombobox
            v-model="languageDraft"
            :options="languageChoices"
            :label="i18n.t('capture.options.languages')"
            :placeholder="i18n.t('capture.options.languages_some')"
            :disabled="languageDisabled"
            @change="addLanguageValue"
          />
          <button
            type="button"
            class="btn small"
            :disabled="languageDisabled || !languageDraft.trim()"
            @click="addLanguage"
          >
            {{ i18n.t("ui.add") }}
          </button>
        </div>
      </div>
      <p v-if="!includes.translations && originalLanguage" class="co-help">
        {{ languageName(originalLanguage, i18n.locale) }}
      </p>
      <p v-if="!includes.translations && !originalLanguage" class="co-help">
        {{ i18n.t("capture.options.original_language_required") }}
      </p>
      <p
        v-if="!includes.translations && languages !== null && languages.length !== 1"
        class="co-invalid"
        role="alert"
      >
        {{ i18n.t("capture.options.need_exact_language") }}
      </p>
      <p
        v-else-if="languages !== null && !languages.length && !languageDisabled"
        class="co-invalid"
        role="alert"
      >
        {{ i18n.t("capture.options.need_language") }}
      </p>
      <small class="co-help">{{ i18n.t("capture.options.languages_help") }}</small>
    </fieldset>
  </div>
</template>

<style scoped>
.capture-options {
  display: grid;
  gap: 16px;
}
fieldset {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
}
legend {
  padding: 0 4px;
  font-weight: var(--fw-bold);
}
fieldset > label {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 8px;
  align-items: start;
}
fieldset > label.nested {
  margin-inline-start: 24px;
}
fieldset > label span {
  display: grid;
  gap: 2px;
}
fieldset small,
.co-help {
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.co-languages {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 6px 12px;
  max-height: 220px;
  overflow: auto;
  padding: 6px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
}
.co-languages label {
  display: flex;
  gap: 6px;
  align-items: center;
}
.co-language-add {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  grid-column: 1 / -1;
}
.co-language-add input {
  min-width: 10rem;
  flex: 1 1 12rem;
}
.co-invalid {
  margin: 0;
  color: var(--tone-danger-fg);
  font-size: var(--fs-sm);
}
</style>
