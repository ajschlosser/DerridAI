<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { CorpusBuild } from "../api/pdfCorpus";
import { groupBuildWarnings, currentWarningRecordIds } from "../domain/corpusBuildPresentation";

const props=defineProps<{warnings:string[];issueSummary?:CorpusBuild["metadata_issue_summary"];disabled?:boolean}>();
const emit=defineEmits<{review:[recordId:string]}>();
const i18n=useI18nStore();
const groups=computed(()=>groupBuildWarnings(props.warnings).map(group=>({...group,recordIds:currentWarningRecordIds(group.messages,props.issueSummary)})));
</script>

<template>
  <details v-if="warnings.length" class="warnings build-warnings">
    <summary>{{i18n.tf('pdf_corpus.warnings_count','{count} build warning(s)',{count:warnings.length})}} <span>{{i18n.t('pdf_corpus.warning_details_hint','Inspect grouped messages')}}</span></summary>
    <div class="warning-groups">
      <p>{{i18n.t('pdf_corpus.warning_count_help','Warning entries are separate from affected records and failed tasks. Inspect the original messages before acting.')}}</p>
      <details v-for="group in groups" :key="group.key" class="warning-group">
        <summary><span>{{group.label}}</span> <b>{{i18n.tf('pdf_corpus.warning_entries','{count} warning(s)',{count:group.messages.length})}}</b></summary>
        <div v-if="group.recordIds.length" class="warning-records">
          <p>{{i18n.t('pdf_corpus.warning_current_records','These records also appear in the current metadata issue summary. Historical warnings may describe an earlier failure.')}}</p>
          <button v-for="recordId in group.recordIds" :key="recordId" type="button" class="btn" :disabled="disabled" @click="emit('review',recordId)">{{i18n.tf('pdf_corpus.warning_review_record','Review current metadata: {record}',{record:recordId})}}</button>
        </div>
        <ol><li v-for="(message,index) in group.messages" :key="index">{{message}}</li></ol>
      </details>
    </div>
  </details>
</template>

<style scoped>
.build-warnings{border:1px solid var(--tone-warn-border);border-radius:9px;background:var(--tone-warn-bg);color:var(--tone-warn-fg);font-size:.875rem}
summary{cursor:pointer;padding:10px 12px;overflow-wrap:anywhere;font-weight:700}
summary>span:last-child{font-weight:400}.build-warnings>summary>span{margin-inline-start:12px}
.warning-groups{display:grid;gap:8px;padding:0 12px 12px}.warning-groups>p{margin:0;line-height:1.5}.warning-group{background:var(--card);border:1px solid var(--line);border-radius:7px;color:var(--text)}.warning-group summary b{margin-inline-start:10px;white-space:nowrap;font-size:.8125rem}.warning-group ol{max-height:280px;overflow:auto;margin:0;padding:0 14px 12px 32px;line-height:1.5;overflow-wrap:anywhere}.warning-group li+li{margin-top:7px}summary:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.warning-records{display:grid;gap:8px;padding:0 12px 12px}.warning-records p{margin:0;line-height:1.5}.warning-records button{min-height:44px;white-space:normal;overflow-wrap:anywhere;text-align:start}.warning-records button:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
</style>
