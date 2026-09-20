<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import { APP_GIT_COMMIT, APP_VERSION, COPYRIGHT_YEAR } from "../buildInfo";

const props = withDefaults(defineProps<{
  showCopyright?: boolean;
  showCommit?: boolean;
  compact?: boolean;
  landmark?: boolean;
}>(), {
  showCopyright: true,
  showCommit: false,
  compact: false,
  landmark: false,
});

const i18n = useI18nStore();
const holder = computed(() => i18n.t("about.copyright_holder", "The New England Transcendental Club of California"));
const copyright = computed(() => i18n.tf("about.copyright", "© {year} {holder}", {year: COPYRIGHT_YEAR, holder: holder.value}));
const product = computed(() => i18n.tf("about.product_version", "DerridAI {version}", {version: APP_VERSION}));
const commitLabel = computed(() => {
  const commit = String(APP_GIT_COMMIT || "").trim();
  return commit ? i18n.tf("about.build_commit", "Build {commit}", {commit}) : "";
});
</script>

<template>
  <div
    class="app-build-info"
    :class="{compact: props.compact}"
    :role="props.landmark ? 'contentinfo' : undefined"
    :aria-label="i18n.t('about.title', 'About DerridAI')"
  >
    <p v-if="props.showCopyright">{{ copyright }}</p>
    <p>{{ product }}</p>
    <p v-if="props.showCommit && commitLabel">{{ commitLabel }}</p>
  </div>
</template>

<style scoped>
.app-build-info{
  display:grid;
  gap:2px;
  color:var(--muted);
  font-size:.8125rem;
  line-height:1.45;
}
.app-build-info p{margin:0}
.app-build-info.compact{gap:1px}
</style>
