<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppIcon from "../components/AppIcon.vue";
import SystemDataAdvanced from "../components/system-data/SystemDataAdvanced.vue";
import SystemDataDatabases from "../components/system-data/SystemDataDatabases.vue";
import SystemDataMetadataExamples from "../components/system-data/SystemDataMetadataExamples.vue";
import SystemDataOverview from "../components/system-data/SystemDataOverview.vue";
import SystemDataResponses from "../components/system-data/SystemDataResponses.vue";
import { useI18nStore } from "../stores/i18n";

type Section = "overview" | "responses" | "metadata" | "databases" | "advanced";

const route = useRoute();
const router = useRouter();
const i18n = useI18nStore();

const sections: Array<{ id: Section; labelKey: string; fallback: string; icon: string }> = [
  { id: "overview", labelKey: "runtime.system_overview", fallback: "Overview", icon: "dashboard" },
  { id: "responses", labelKey: "runtime.system_responses", fallback: "Responses", icon: "record" },
  { id: "metadata", labelKey: "runtime.system_metadata_examples", fallback: "Metadata examples", icon: "spark" },
  { id: "databases", labelKey: "runtime.system_databases", fallback: "Databases", icon: "database" },
  { id: "advanced", labelKey: "runtime.system_advanced", fallback: "Advanced", icon: "gear" },
];

const activeSection = computed<Section>(() => {
  const requested = String(route.query.section || "overview");
  return sections.some((item) => item.id === requested) ? (requested as Section) : "overview";
});
const activeComponent = computed(() => ({
  overview: SystemDataOverview,
  responses: SystemDataResponses,
  metadata: SystemDataMetadataExamples,
  databases: SystemDataDatabases,
  advanced: SystemDataAdvanced,
})[activeSection.value]);

function t(key: string, fallback: string) {
  return i18n.t(key, fallback);
}

function setSection(section: Section) {
  void router.push({ path: "/system-data", query: { ...route.query, section } });
}
</script>

<template>
  <main id="main" class="runtime-surface system-data-page">
    <header class="page-header">
      <div>
        <h1>{{ t("runtime.system_data", "System Data") }}</h1>
        <p>
          {{
            t(
              "runtime.system_data_help",
              "Inspect application storage, trace derived metadata, and manage saved research responses.",
            )
          }}
        </p>
      </div>
    </header>

    <div class="mobile-section-picker">
      <label for="system-data-section">{{ t("runtime.system_workspace", "Workspace") }}</label>
      <select
        id="system-data-section"
        class="control"
        :value="activeSection"
        @change="setSection(($event.target as HTMLSelectElement).value as Section)"
      >
        <option v-for="item in sections" :key="item.id" :value="item.id">
          {{ t(item.labelKey, item.fallback) }}
        </option>
      </select>
    </div>

    <div class="workspace-shell">
      <nav class="section-rail" :aria-label="t('runtime.system_workspace', 'System Data workspaces')">
        <button
          v-for="item in sections"
          :key="item.id"
          type="button"
          :class="{ active: activeSection === item.id }"
          :aria-current="activeSection === item.id ? 'page' : undefined"
          @click="setSection(item.id)"
        >
          <AppIcon :name="item.icon" />
          <span>{{ t(item.labelKey, item.fallback) }}</span>
        </button>
      </nav>

      <section class="workspace" aria-live="polite">
        <KeepAlive>
          <component :is="activeComponent" @open-section="setSection" />
        </KeepAlive>
      </section>
    </div>
  </main>
</template>

<style scoped>
.system-data-page {
  display: grid;
  gap: 22px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: end;
}
.page-header h1 {
  margin: 0;
  font-size: clamp(1.75rem, 2vw, 2.3rem);
  letter-spacing: -0.035em;
}
.page-header p {
  max-width: 760px;
  margin: 7px 0 0;
  color: var(--muted);
  line-height: 1.55;
}
.workspace-shell {
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
  gap: 24px;
  align-items: start;
}
.section-rail {
  position: sticky;
  top: 18px;
  display: grid;
  gap: 4px;
}
.section-rail button {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: var(--muted);
  font: inherit;
  font-weight: 650;
  text-align: left;
  cursor: pointer;
}
.section-rail button:hover {
  background: var(--soft);
  color: inherit;
}
.section-rail button.active {
  border-color: var(--line);
  background: var(--card);
  color: inherit;
  box-shadow: 0 1px 2px color-mix(in srgb, currentColor 7%, transparent);
}
.section-rail :deep(svg) {
  width: 18px;
  height: 18px;
}
.workspace {
  min-width: 0;
}
.mobile-section-picker {
  display: none;
}
@media (prefers-reduced-motion: no-preference) {
  .workspace {
    animation: workspace-in 140ms ease-out;
  }
  @keyframes workspace-in {
    from { opacity: .72; transform: translateY(2px); }
    to { opacity: 1; transform: none; }
  }
}
@media (max-width: 820px) {
  .workspace-shell {
    grid-template-columns: 1fr;
    gap: 14px;
  }
  .section-rail {
    display: none;
  }
  .mobile-section-picker {
    display: grid;
    gap: 6px;
  }
  .mobile-section-picker label {
    color: var(--muted);
    font-size: .78rem;
    font-weight: 700;
  }
}
</style>
