<script setup lang="ts">
import { ref } from "vue";
import AppIcon from "./AppIcon.vue";
import { useI18nStore } from "../stores/i18n";

const props = withDefaults(defineProps<{
  languageCount?: number;
  keyCount?: number;
  title?: string;
  description?: string;
}>(), { languageCount: 0, keyCount: 0, title: "", description: "" });
const emit = defineEmits<{ install: [] }>();
const i18n = useI18nStore();
const installButton = ref<HTMLButtonElement | null>(null);
defineExpose({ focusInstall: () => installButton.value?.focus() });
</script>

<template>
  <header class="language-workspace-header">
    <div class="language-workspace-copy">
      <p>{{ i18n.t("section.system", "System") }} · {{ i18n.t("language.workspace_kicker", "Localization studio") }}</p>
      <h1>{{ props.title || i18n.t("language.page_title", "Languages & internationalization") }}</h1>
      <span>{{ props.description || i18n.t("language.page_description_modern", "Manage interface locales from one bilingual translation workspace. English is the canonical source; installed locales stay editable and auditable.") }}</span>
    </div>
    <div class="language-workspace-actions">
      <div class="language-workspace-stats" :aria-label="i18n.t('language.localization_summary','Localization summary')">
        <span><b>{{ props.languageCount }}</b>{{ i18n.t("language.locales", "Locales") }}</span>
        <span><b>{{ props.keyCount.toLocaleString(i18n.locale) }}</b>{{ i18n.t("language.source_strings", "English strings") }}</span>
      </div>
      <button ref="installButton" type="button" class="language-install-primary" @click="emit('install')"><AppIcon name="plus" />{{ i18n.t("language.install", "Install language") }}</button>
    </div>
  </header>
</template>

<style scoped>
.language-workspace-header{position:sticky;top:0;z-index:18;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:24px;align-items:center;padding:18px 20px;border:1px solid var(--line,#dfe6ed);border-radius:16px;background:color-mix(in srgb,#fff 94%,var(--ui-accent-soft,#eef7f1));box-shadow:0 8px 28px rgba(15,23,42,.07);backdrop-filter:blur(14px)}.language-workspace-copy{min-width:0}.language-workspace-copy p{margin:0 0 3px;color:var(--ui-accent-dark,#286442);font-size:.8125rem;font-weight:850;letter-spacing:.08em;text-transform:uppercase}.language-workspace-copy h1{margin:0;font:600 clamp(24px,2.2vw,33px)/1.08 Georgia,"Times New Roman",serif;letter-spacing:-.018em;color:#1d2c3f}.language-workspace-copy span{display:block;max-width:780px;margin-top:7px;color:#65748a;font-size:12.5px;line-height:1.5}.language-workspace-actions{display:flex;align-items:center;gap:12px}.language-workspace-stats{display:flex;gap:7px}.language-workspace-stats span{min-width:82px;display:grid;gap:1px;padding:8px 10px;border:1px solid #dfe7e2;border-radius:10px;background:rgba(255,255,255,.82);color:#6b7888;font-size:.8125rem;text-transform:uppercase;letter-spacing:.04em}.language-workspace-stats b{font-size:16px;color:#26374c;letter-spacing:0}.language-install-primary{min-height:42px;display:inline-flex;align-items:center;gap:7px;border:1px solid color-mix(in srgb,var(--ui-accent,#3c8d62) 76%,#173324);border-radius:10px;background:var(--ui-accent,#3c8d62);padding:0 14px;color:#fff;font-weight:750;cursor:pointer}.language-install-primary :deep(svg){width:16px;height:16px}.language-install-primary:focus-visible{outline:3px solid color-mix(in srgb,var(--ui-accent,#3c8d62) 48%,#fff);outline-offset:2px}@media(max-width:900px){.language-workspace-header{grid-template-columns:1fr}.language-workspace-actions{justify-content:space-between}.language-workspace-copy span{max-width:none}}@media(max-width:560px){.language-workspace-stats{display:none}.language-install-primary{width:100%;justify-content:center}}
</style>
