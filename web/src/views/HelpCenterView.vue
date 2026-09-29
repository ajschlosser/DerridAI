<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { visibleHelp } from "../domain/helpTopics";
import { useAuthStore } from "../stores/auth";
import { useI18nStore } from "../stores/i18n";
import UiPageHeader from "../components/ui/UiPageHeader.vue";

// Explains where a user's decisions matter and what they change downstream.
const i18n = useI18nStore();
const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const query = ref(String(route.query.q || ""));
let applyingRouteState = false;
const sections = computed(() => visibleHelp(auth.isAdmin, query.value, (key) => i18n.t(key)));
const matchCount = computed(() =>
  sections.value.reduce((total, section) => total + section.entries.length, 0),
);

watch(query, (value) => {
  if (applyingRouteState) return;
  void router.replace({
    name: "help",
    query: { ...route.query, q: value.trim() || undefined },
  });
});

watch(
  () => route.query.q,
  (value) => {
    const next = String(value || "");
    if (next === query.value) return;
    applyingRouteState = true;
    query.value = next;
    applyingRouteState = false;
  },
);
</script>

<template>
  <section class="help-center">
    <UiPageHeader :title="i18n.t('help.title')" :description="i18n.t('help.intro')" />
    <label class="help-search">
      <span>{{ i18n.t("help.search") }}</span>
      <input v-model="query" class="control" type="search" />
    </label>
    <p class="sr-only" role="status" aria-live="polite">
      {{ query ? i18n.tf("help.result_count", { count: matchCount }) : "" }}
    </p>
    <p v-if="!sections.length" class="help-empty">
      {{ i18n.tf("help.no_results", { query }) }}
    </p>
    <section
      v-for="section in sections"
      :key="section.id"
      class="help-section"
      :aria-labelledby="`help-${section.id}`"
    >
      <h2 :id="`help-${section.id}`">{{ section.title }}</h2>
      <details v-for="entry in section.entries" :key="entry.id" class="help-entry" :open="!!query">
        <summary>{{ entry.question }}</summary>
        <p>{{ entry.answer }}</p>
        <h3>{{ i18n.t("help.impact_heading") }}</h3>
        <p>{{ entry.impact }}</p>
      </details>
    </section>
  </section>
</template>

<style scoped>
.help-center {
  display: grid;
  gap: 16px;
  max-inline-size: 60rem;
}
.help-search {
  display: grid;
  gap: 4px;
  max-inline-size: 28rem;
  font-size: 0.8125rem;
  font-weight: 650;
}
.help-empty {
  color: var(--muted);
}
.help-section {
  display: grid;
  gap: 8px;
}
.help-section h2 {
  margin: 8px 0 0;
  font-size: 1.0625rem;
}
.help-entry {
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--card);
}
.help-entry summary {
  cursor: pointer;
  font-weight: 650;
}
.help-entry p {
  margin: 8px 0 0;
  line-height: 1.5;
}
.help-entry h3 {
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 0.8125rem;
}
</style>
