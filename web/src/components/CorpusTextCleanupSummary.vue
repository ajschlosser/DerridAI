<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import UiStatusBadge from "./ui/UiStatusBadge.vue";

const props=defineProps<{summary?:{enabled?:boolean;records_changed?:number;changes?:number;removed_lines?:number;recurring_line_patterns?:number;rules?:string[]}}>();
const i18n=useI18nStore();
const enabled=computed(()=>Boolean(props.summary?.enabled));
const changed=computed(()=>Number(props.summary?.records_changed||0));
</script>

<template>
  <section v-if="summary" class="cleanup-summary" :aria-label="i18n.t('pdf_corpus.automatic_text_cleanup')">
    <div class="cleanup-copy">
      <b>{{i18n.t('pdf_corpus.automatic_text_cleanup')}}</b>
      <span v-if="enabled">{{i18n.tf('pdf_corpus.cleanup_pre_enrichment_summary', {records:changed,changes:Number(summary.changes||0),removed:Number(summary.removed_lines||0)})}}</span>
      <span v-else>{{i18n.t('pdf_corpus.cleanup_disabled_summary')}}</span>
    </div>
    <UiStatusBadge :tone="enabled&&changed>0?'success':'neutral'" :label="enabled?i18n.t('pdf_corpus.cleanup_applied'):i18n.t('pdf_corpus.cleanup_not_applied')" />
  </section>
</template>

<style scoped>
.cleanup-summary{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:11px 13px;border:1px solid var(--line);border-radius:10px;background:var(--panel)}.cleanup-copy{display:grid;gap:3px;min-width:0}.cleanup-copy b{font-size:.875rem}.cleanup-copy span{font-size:.8125rem;line-height:1.45;color:var(--muted)}@media(max-width:680px){.cleanup-summary{align-items:flex-start;flex-direction:column}}
</style>
