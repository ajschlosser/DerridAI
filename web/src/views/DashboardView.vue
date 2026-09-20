<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { onMounted } from "vue";
import DashboardHero from "../components/dashboard/DashboardHero.vue";
import DashboardOverview from "../components/dashboard/DashboardOverview.vue";
import DashboardSearchPanel from "../components/dashboard/DashboardSearchPanel.vue";
import DashboardWorks from "../components/dashboard/DashboardWorks.vue";
import UiButton from "../components/ui/UiButton.vue";
import { useDashboard } from "../composables/useDashboard";
import { useI18nStore } from "../stores/i18n";
import { useAuthStore } from "../stores/auth";
import { useShellStore } from "../stores/shell";

const i18n = useI18nStore();
const auth = useAuthStore();
const shell = useShellStore();
const { snapshot, loading, error, refresh: reload, search, openView, searchWork } = useDashboard();
async function refresh() {
  await reload();
  shell.sync();
}
onMounted(() => {
  void refresh();
});
</script>
<template>
  <main class="dashboard-page vue-native-page" aria-labelledby="home-page-title">
    <div v-if="loading && !snapshot" class="page-loading" role="status" aria-live="polite">
      {{ i18n.t("dashboard.loading", "Loading Home") }}
    </div>
    <section v-else-if="error" class="dashboard-error" role="alert">
      <h1>{{ i18n.t("dashboard.load_failed", "Could not load Home") }}</h1>
      <p>{{ error }}</p>
      <UiButton :label="i18n.t('ui.retry', 'Retry')" @click="refresh" />
    </section>
    <template v-else-if="snapshot">
      <DashboardHero
        @search="search(snapshot.query, '', snapshot.mode)"
        @works="openView('works')"
      />
      <DashboardSearchPanel
        :query="snapshot.query"
        :mode="snapshot.mode"
        :works="snapshot.works"
        @submit="search"
      />
      <DashboardOverview
        :totals="snapshot.totals"
        @works="openView('works')"
        @records="openView(auth.isResearcher ? 'vector' : 'list')"
        @databases="openView('vector')"
      />
      <DashboardWorks
        :works="snapshot.works"
        @works="openView('works')"
        @search-work="searchWork"
      />
    </template>
  </main>
</template>
<style scoped>
.dashboard-page {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
  gap: var(--space-4);
}
.dashboard-page > :nth-child(4) {
  grid-column: 1/-1;
}
.dashboard-error {
  padding: var(--space-6);
}
@media (max-width: 900px) {
  .dashboard-page {
    grid-template-columns: 1fr;
  }
}
</style>
