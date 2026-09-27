<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, useId } from "vue";
import type { SourceProviderId, SourceProviderInfo } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import { languageName, sortLanguageCodes } from "../../domain/languages";
import type { CaptureIncludes } from "../../domain/captureReview";

/**
 * Libraries, contribution roles and languages for a capture. Languages default to "all"; the
 * choosable list is the Wikisource projects the API discovered, never a list fixed in the browser.
 */
const props = defineProps<{
  providers: SourceProviderId[];
  includes: CaptureIncludes;
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
}
function toggleLanguage(code: string, on: boolean) {
  const next = new Set(props.languages || []);
  if (on) next.add(code);
  else next.delete(code);
  emit("update:languages", [...next]);
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
          :disabled="key === 'translations' && !includes.authored"
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
        <label v-for="code in projectCodes" :key="code">
          <input
            type="checkbox"
            :checked="languages.includes(code)"
            :data-language="code"
            @change="toggleLanguage(code, ($event.target as HTMLInputElement).checked)"
          />
          <span>{{ languageName(code, i18n.locale) }}</span>
        </label>
      </div>
      <p v-if="languages !== null && !languages.length" class="co-invalid" role="alert">
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
.co-invalid {
  margin: 0;
  color: var(--tone-danger-fg);
  font-size: var(--fs-sm);
}
</style>
