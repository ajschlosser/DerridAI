<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import UiButton from "../ui/UiButton.vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";
import { useI18nStore } from "../../stores/i18n";
import type { VectorCollection } from "../../types/vector";

const props = defineProps<{
  collection: VectorCollection;
  pendingCount?: number;
}>();
const emit = defineEmits<{
  sync: [];
  retrieval: [];
  protection: [];
  delete: [];
}>();
const i18n = useI18nStore();
const status = computed(() => String(props.collection.status || ((props.collection.count || 0) ? "ready" : "empty")).toLowerCase());
const statusTone = computed(() => status.value === "ready" ? "success" : status.value.includes("fail") || status.value === "stale" ? "danger" : status.value === "empty" ? "neutral" : "info");
const providerLabel = computed(() => {
  const provider = props.collection.embedding_provider || "chroma";
  if (provider === "ollama") return `Ollama · ${props.collection.embedding_model || ""}`.trim();
  if (provider === "precomputed") return i18n.t("vector.provider_precomputed");
  return i18n.t("vector.provider_chroma");
});
const syncLabel = computed(() => props.pendingCount
  ? i18n.tf("vector.unsynced_changes_count", {count: Number(props.pendingCount).toLocaleString(i18n.locale)})
  : i18n.t("vector.sync"));
</script>
<template>
  <section class="card vector-collection-hero vector-collection-hero-v037">
    <div class="vector-hero-copy">
      <div class="vector-hero-kicker">
        <span class="section-label">{{ i18n.t("vector.collection") }}</span>
        <UiStatusBadge :label="status.replaceAll('_', ' ')" :tone="statusTone" />
        <UiStatusBadge v-if="collection.protected" :label="i18n.t('vector.protected')" tone="warning" />
      </div>
      <h2>{{ collection.name }}</h2>
      <p v-if="collection.description" class="vector-collection-description">{{ collection.description }}</p>
      <div class="vector-collection-contract">
        <span><b>{{ Number(collection.count || 0).toLocaleString(i18n.locale) }}</b> {{ i18n.t("dynamic.records") }}</span>
        <span>{{ collection.retrieval_mode || "semantic" }}</span>
        <span>{{ providerLabel }}</span>
        <span v-if="collection.embedding_dimension">{{ Number(collection.embedding_dimension).toLocaleString(i18n.locale) }}d</span>
        <span>{{ collection.distance_metric || "l2" }}</span>
        <span v-if="collection.language_codes?.length">{{ collection.language_codes.join(", ") }}</span>
      </div>
      <div class="vector-collection-provenance">
        <span v-if="collection.source_label || collection.source_kind">{{ i18n.t("vector.source") }}: <b>{{ collection.source_label || collection.source_kind }}</b></span>
        <span v-if="collection.last_synced_at">{{ i18n.t("vector.last_synced") }}: <b>{{ new Date(collection.last_synced_at).toLocaleString(i18n.locale) }}</b></span>
        <span v-else>{{ i18n.t("vector.never_synced") }}</span>
        <span v-if="collection.build_id" :title="collection.build_id">{{ i18n.t("vector.build") }}: <code>{{ collection.build_id.slice(-12) }}</code></span>
      </div>
    </div>
    <div class="tools vector-hero-actions">
      <UiButton
        :label="syncLabel"
        icon="database"
        variant="soft"
        :disabled="!pendingCount"
        :disabled-reason="i18n.t('vector.no_unsynced_changes_help')"
        @click="emit('sync')"
      />
      <UiButton :label="i18n.t('vector.test_retrieval')" icon="search" @click="emit('retrieval')" />
      <details class="vector-hero-menu">
        <summary class="btn">{{ i18n.t("ui.more_actions") }}</summary>
        <div class="vector-hero-menu-popover">
          <UiButton :label="collection.protected ? i18n.t('vector.disable_protection') : i18n.t('vector.enable_protection')" :icon="collection.protected ? 'unlock' : 'lock'" @click="emit('protection')" />
          <UiButton
            :label="i18n.t('vector.delete_collection')"
            variant="danger"
            :disabled="Boolean(collection.protected)"
            :disabled-reason="i18n.t('vector.disable_protection_before_delete')"
            @click="emit('delete')"
          />
        </div>
      </details>
    </div>
  </section>
</template>
<style scoped>
.vector-hero-kicker{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.vector-hero-menu-popover{display:grid;gap:6px;min-width:220px;padding:8px}
.vector-collection-hero-v037 {
  display: grid;
  grid-template-columns: minmax(0,1fr) auto;
  gap: 18px;
  align-items: start;
}
.vector-hero-copy {
  min-width: 0;
}
.vector-collection-description {
  margin: 5px 0 10px;
  color: var(--muted);
  max-width: 78ch;
}
.vector-collection-contract,
.vector-collection-provenance {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
  align-items: center;
}
.vector-collection-contract span {
  border: 1px solid var(--line);
  background: var(--panel-2);
  border-radius: 999px;
  padding: 5px 9px;
  font-size: .78rem;
}
.vector-collection-provenance {
  margin-top: 9px;
  color: var(--muted);
  font-size: .76rem;
}
.vector-collection-provenance span+span:before {
  content: "·";
  margin-right: 7px;
}
.vector-collection-provenance code {
  font-size: .8125rem;
}
.vector-hero-actions {
  justify-content: flex-end;
  max-width: 420px;
}
.vector-hero-menu {
  position: relative;
}
.vector-hero-menu>summary {
  list-style: none;
  cursor: pointer;
}
.vector-hero-menu>summary::-webkit-details-marker {
  display: none;
}
@media (max-width:820px) {
  .vector-collection-hero-v037 {
    grid-template-columns: 1fr;
  }
}
@media (max-width:820px) {
  .vector-hero-actions {
    justify-content: flex-start;
    max-width: none;
  }
}
</style>
