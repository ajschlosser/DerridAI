<script setup lang="ts">
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
const props=withDefaults(defineProps<{count:number;canReview?:boolean;canBulkEdit?:boolean}>(),{canReview:false,canBulkEdit:false});
const emit=defineEmits<{review:[];improve:[];bulk:[];clear:[]}>();
const i18n=useI18nStore();
</script>
<template>
  <div v-if="props.count" class="search-selection-bar" role="region" :aria-label="i18n.t('search.selection_actions','Selected record actions')">
    <div class="search-selection-copy"><span class="search-selection-count">{{props.count.toLocaleString(i18n.locale)}}</span><span>{{i18n.t('search.selected_records','selected records')}}</span></div>
    <div class="search-selection-actions">
      <button v-if="canReview" type="button" class="btn soft" @click="emit('review')"><AppIcon name="spark"/>{{i18n.t('search.review_selected','Review with LLM')}}</button>
      <button v-if="canReview" type="button" class="btn" @click="emit('improve')"><AppIcon name="spark"/>{{i18n.t('search.auto_improve_selected','Auto-improve')}}</button>
      <button v-if="canBulkEdit" type="button" class="btn" @click="emit('bulk')"><AppIcon name="edit"/>{{i18n.t('search.bulk_edit_selected','Bulk edit')}}</button>
      <button type="button" class="btn" @click="emit('clear')">{{i18n.t('search.clear_selection','Clear selection')}}</button>
    </div>
  </div>
</template>
