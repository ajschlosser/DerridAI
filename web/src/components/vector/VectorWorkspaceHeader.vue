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
import UiLoadingState from "../ui/UiLoadingState.vue";
import UiButton from "../ui/UiButton.vue";
import UiHealthChip from "../ui/UiHealthChip.vue";
import UiPageHeader from "../ui/UiPageHeader.vue";
import { useI18nStore } from "../../stores/i18n";
import type { ChromaHealth } from "../../types/vector";

const props = defineProps<{
  health: ChromaHealth | null;
  collectionCount?: number;
  healthLoading?: boolean;
  canCreate?: boolean;
  createDisabledReason?: string;
}>();
const emit = defineEmits<{ create: []; connection: [] }>();
const i18n = useI18nStore();
</script>
<template>
  <UiPageHeader
    class="vector-workspace-header"
    :kicker="i18n.t('section.corpus_management', 'Corpus Management')"
    :title="i18n.t('nav.vector', 'Corpus Data')"
    :description="i18n.t('vector.page_help')"
    title-id="vector-page-title"
    :actions-label="i18n.t('vector.manage_collections')"
  >
    <template #actions>
      <div class="vector-workspace-actions">
        <span v-if="props.collectionCount" class="badge">
          {{ Number(props.collectionCount).toLocaleString(i18n.locale) }}
          {{ i18n.t("vector.collections") }}
        </span>
        <UiLoadingState v-if="healthLoading" variant="inline" :label="i18n.t('loading.health')" />
        <UiHealthChip
          v-else
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
          :disabled="canCreate === false"
          :disabled-reason="createDisabledReason"
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
