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
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
const props = withDefaults(
  defineProps<{ count: number; canReview?: boolean; canBulkEdit?: boolean }>(),
  { canReview: false, canBulkEdit: false },
);
const emit = defineEmits<{ review: []; improve: []; bulk: []; clear: [] }>();
const i18n = useI18nStore();
</script>
<template>
  <div
    v-if="props.count"
    class="search-selection-bar"
    role="region"
    :aria-label="i18n.t('search.selection_actions')"
  >
    <div class="search-selection-copy">
      <span class="search-selection-count">{{ props.count.toLocaleString(i18n.locale) }}</span
      ><span>{{ i18n.t("search.selected_records") }}</span>
    </div>
    <div class="search-selection-actions">
      <button v-if="canReview" type="button" class="btn soft" @click="emit('review')">
        <AppIcon name="spark" />{{ i18n.t("search.review_selected") }}
      </button>
      <button v-if="canReview" type="button" class="btn" @click="emit('improve')">
        <AppIcon name="spark" />{{ i18n.t("search.auto_improve_selected") }}
      </button>
      <button v-if="canBulkEdit" type="button" class="btn" @click="emit('bulk')">
        <AppIcon name="edit" />{{ i18n.t("search.bulk_edit_selected") }}
      </button>
      <button type="button" class="btn" @click="emit('clear')">
        {{ i18n.t("search.clear_selection") }}
      </button>
    </div>
  </div>
</template>
