<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import UiButton from "../ui/UiButton.vue";
import UiHealthChip from "../ui/UiHealthChip.vue";
import { useI18nStore } from "../../stores/i18n";
import type { ChromaHealth } from "../../types/vector";

const props = defineProps<{
  health: ChromaHealth | null;
  collectionCount?: number;
}>();
const emit = defineEmits<{create: []; connection: []}>();
const i18n = useI18nStore();
</script>
<template>
  <header class="vector-workspace-header">
    <div class="vector-workspace-copy">
      <p>{{ i18n.t("section.storage", "Storage") }}</p>
      <h1 id="vector-page-title">{{ i18n.t("nav.vector", "Vector Stores") }}</h1>
      <span>{{ i18n.t("vector.page_help", "Create, sync, browse, search, and export persistent Chroma collections used by DerridAI.") }}</span>
    </div>
    <div class="vector-workspace-actions" :aria-label="i18n.t('vector.manage_collections', 'Manage collections')">
      <span v-if="props.collectionCount" class="badge">{{ Number(props.collectionCount).toLocaleString(i18n.locale) }} {{ i18n.t("vector.collections", "collections") }}</span>
      <UiHealthChip
        :available="Boolean(props.health?.available)"
        :label="props.health?.available ? (props.health.identity || i18n.t('vector.health_ready', 'Chroma ready')) : i18n.t('vector.health_unavailable', 'Chroma unavailable')"
        :detail="props.health?.error || ''"
      />
      <UiButton :label="i18n.t('vector.open_connection', 'Connection settings')" icon="gear" @click="emit('connection')" />
      <UiButton :label="i18n.t('vector.new_collection_short', 'New')" icon="plus" variant="primary" @click="emit('create')" />
    </div>
  </header>
</template>
<style scoped>
.vector-workspace-header{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px;align-items:center;padding:4px 2px}
.vector-workspace-copy p{margin:0 0 3px;color:var(--accent-2,var(--accent));font-size:.8125rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase}
.vector-workspace-copy h1{margin:0;font:600 clamp(24px,2.2vw,32px)/1.1 Georgia,"Times New Roman",serif;letter-spacing:-.02em}
.vector-workspace-copy span{display:block;max-width:72ch;margin-top:8px;color:var(--muted);font-size:.8125rem;line-height:1.5}
.vector-workspace-actions{display:flex;flex-wrap:wrap;align-items:center;gap:8px;justify-content:flex-end}
@media(max-width:800px){.vector-workspace-header{grid-template-columns:1fr}.vector-workspace-actions{justify-content:flex-start}}
</style>
