<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import UiButton from "../ui/UiButton.vue";
import UiHealthChip from "../ui/UiHealthChip.vue";
import UiPageHeader from "../ui/UiPageHeader.vue";
import { useI18nStore } from "../../stores/i18n";
import type { ChromaHealth } from "../../types/vector";

const props = defineProps<{
  health: ChromaHealth | null;
  collectionCount?: number;
}>();
const emit = defineEmits<{ create: []; connection: [] }>();
const i18n = useI18nStore();
</script>
<template>
  <UiPageHeader
    class="vector-workspace-header"
    :kicker="i18n.t('section.storage')"
    :title="i18n.t('nav.vector')"
    :description="
      i18n.t('vector.page_help')
    "
    title-id="vector-page-title"
    :actions-label="i18n.t('vector.manage_collections')"
  >
    <template #actions>
      <div class="vector-workspace-actions">
        <span v-if="props.collectionCount" class="badge">
          {{ Number(props.collectionCount).toLocaleString(i18n.locale) }}
          {{ i18n.t("vector.collections") }}
        </span>
        <UiHealthChip
          :available="Boolean(props.health?.available)"
          :label="
            props.health?.available
              ? props.health.identity || i18n.t('vector.health_ready')
              : i18n.t('vector.health_unavailable')
          "
          :detail="props.health?.error || ''"
        />
        <UiButton
          :label="i18n.t('vector.open_connection')"
          icon="gear"
          @click="emit('connection')"
        />
        <UiButton
          :label="i18n.t('vector.new_collection_short')"
          icon="plus"
          variant="primary"
          @click="emit('create')"
        />
      </div>
    </template>
  </UiPageHeader>
</template>
<style scoped>
.vector-workspace-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  justify-content: flex-end;
}
</style>
