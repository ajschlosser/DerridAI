<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { CorpusBuild } from "../api/pdfCorpus";
import { metadataTaskProgress } from "../domain/corpusBuildPresentation";

const props=defineProps<{build:CorpusBuild;disabled?:boolean}>();
const emit=defineEmits<{settle:[];cancel:[]}>();
const i18n=useI18nStore();
const tasks=computed(()=>metadataTaskProgress(props.build));
const running=computed(()=>tasks.value.running??0);
const countText=(value:number|null)=>value===null?'—':value;
const active=computed(()=>Array.isArray(props.build.metadata_active_tasks)?props.build.metadata_active_tasks:[]);
const lastProgress=computed(()=>props.build.metadata_last_progress_at?new Date(props.build.metadata_last_progress_at).toLocaleTimeString():i18n.t("pdf_corpus.not_yet","not yet"));
function elapsedSince(value?:string|null):number{if(!value)return 0;const ms=Date.now()-new Date(value).getTime();return Number.isFinite(ms)&&ms>0?ms:0}
function formatDuration(ms:number):string{const totalSeconds=Math.max(0,Math.round(ms/1000));const minutes=Math.floor(totalSeconds/60);const seconds=totalSeconds%60;return minutes?`${minutes}m ${String(seconds).padStart(2,"0")}s`:`${seconds}s`}
const elapsed=computed(()=>formatDuration(elapsedSince(props.build.metadata_started_at)));
const eta=computed(()=>{
  const elapsedMs=elapsedSince(props.build.metadata_started_at);
  const {determinate,settled,total}=tasks.value;
  if(!elapsedMs||!determinate||settled===null||total===null||settled<=0||settled>=total)return "";
  return formatDuration((elapsedMs/settled)*(total-settled));
});
function activeElapsed(startedAt?:string|null){return startedAt?formatDuration(elapsedSince(startedAt)):""}
const stalled=computed(()=>{
  if(!props.build.metadata_last_progress_at||String(props.build.stage)!=="enriching")return false;
  const configured=(props.build.request?.stage_timeouts||{}) as Record<string,unknown>;
  const metadataDeadlines=["discourse","quotation","indexing"].map(key=>Number(configured[key]||240)).filter(Number.isFinite);
  const thresholdSeconds=Math.max(90,Math.min(600,Math.max(...metadataDeadlines,240)+30));
  const ms=Date.now()-new Date(props.build.metadata_last_progress_at).getTime();
  return Number.isFinite(ms)&&ms>thresholdSeconds*1000&&running.value>0;
});
function taskLabel(task:string){return i18n.t(`pdf_corpus.metadata_task.${task}`,task)}
</script>

<template>
  <section class="metadata-live-status" :data-stalled="stalled?'true':'false'" role="status" aria-live="polite" aria-atomic="false">
    <div class="status-main">
      <div class="status-title-row">
        <div>
          <span class="eyebrow">{{i18n.t('pdf_corpus.metadata_enrichment','Metadata enrichment')}}</span>
          <h2>{{stalled?i18n.t('pdf_corpus.metadata_stalled_title','Metadata progress may be stalled'):i18n.t('pdf_corpus.metadata_live_title','Automatic metadata is running')}}</h2>
        </div>
        <strong class="status-count" v-if="tasks.determinate">{{i18n.tf('pdf_corpus.metadata_settled_count','{settled} of {total} tasks settled',{settled:countText(tasks.settled),total:countText(tasks.total)})}}</strong>
        <strong class="status-count" v-else>{{tasks.inconsistent?i18n.t('pdf_corpus.metadata_counts_updating','Updating task counts'):i18n.t('pdf_corpus.metadata_counts_unavailable','Task total unavailable')}}</strong>
      </div>
      <p>{{i18n.tf('pdf_corpus.metadata_task_outcomes','{complete} completed · {failed} failed · {skipped} skipped · {running} running · {queued} queued',{complete:countText(tasks.complete),failed:countText(tasks.failed),skipped:countText(tasks.skipped),running:countText(tasks.running),queued:countText(tasks.queued)})}}</p>
      <div class="progress-track" :data-indeterminate="!tasks.determinate" :aria-label="i18n.t('pdf_corpus.metadata_task_progress','Metadata task progress')" :aria-valuenow="tasks.determinate?(tasks.settled??undefined):undefined" :aria-valuemin="tasks.determinate?0:undefined" :aria-valuemax="tasks.determinate?(tasks.total??undefined):undefined" role="progressbar"><span :style="{width:tasks.fraction!==null?`${tasks.fraction*100}%`:'35%'}"></span></div>
    </div>



    <div class="status-actions">
      <button type="button" class="btn" :disabled="disabled||Boolean(build.metadata_settle_requested)" @click="emit('settle')">{{build.metadata_settle_requested?i18n.t('pdf_corpus.settle_requested','Settling remaining tasks…'):i18n.t('pdf_corpus.continue_unresolved','Continue with unresolved metadata')}}</button>
      <button type="button" class="btn" :disabled="disabled" @click="emit('cancel')">{{i18n.t('pdf_corpus.cancel_build','Cancel build')}}</button>
    </div>
    <details class="activity-details">
      <summary>{{i18n.t('pdf_corpus.metadata_activity_details','Task activity and timing')}}</summary>
      <p class="status-secondary">{{i18n.t('pdf_corpus.elapsed','Elapsed')}}: {{elapsed}}<template v-if="eta"> · {{i18n.t('pdf_corpus.eta','ETA')}}: ~{{eta}}</template> · {{i18n.t('pdf_corpus.last_progress','Last settled task')}}: {{lastProgress}} · {{i18n.t('pdf_corpus.concurrency','Concurrency')}}: {{build.metadata_concurrency||1}}</p>
    <div v-if="active.length" class="active-tasks" :aria-label="i18n.t('pdf_corpus.active_metadata_tasks','Active metadata tasks')">
      <b>{{i18n.t('pdf_corpus.active_now','Active now')}}</b>
      <ul><li v-for="item in active.slice(0,6)" :key="`${item.record_id}-${item.task}`"><span>{{item.record_id}}</span><strong>{{taskLabel(String(item.task||''))}}<small v-if="activeElapsed(item.started_at)"> · {{activeElapsed(item.started_at)}}</small></strong></li></ul>
    </div>
    </details>
  </section>
</template>

<style scoped>
.metadata-live-status{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center;padding:10px 14px;border:1px solid var(--line);border-radius:12px;background:var(--card)}
.metadata-live-status[data-stalled="true"]{border-color:var(--tone-warn-border);background:var(--tone-warn-bg)}.status-main{display:grid;gap:4px;min-width:0}.status-title-row{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}.eyebrow{font-size:.8125rem;line-height:1.35;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:800}.status-title-row h2{margin:2px 0 0;font-size:1.0625rem;line-height:1.3}.status-count{font-size:.875rem;overflow-wrap:anywhere}.status-main p{margin:0;font-size:0.8125rem;line-height:1.45}.status-secondary{color:var(--muted)}.progress-track{height:8px;overflow:hidden;border-radius:999px;background:var(--soft)}.progress-track[data-indeterminate="true"] span{opacity:.45}.progress-track span{display:block;height:100%;background:var(--accent);transition:width .2s ease}.activity-details{grid-column:1/-1;font-size:.8125rem}.activity-details>summary{cursor:pointer;font-weight:700}.activity-details>summary:focus-visible{outline:3px solid var(--accent);outline-offset:2px}.activity-details[open]{display:grid;gap:8px}.active-tasks{display:grid;gap:7px;min-width:0}.active-tasks>b{font-size:0.8125rem}.active-tasks ul{list-style:none;margin:0;padding:0;display:grid;gap:4px}.active-tasks li{display:flex;justify-content:space-between;gap:10px;font-size:.8125rem;line-height:1.4}.active-tasks li span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--muted)}.active-tasks li strong{white-space:nowrap}.active-tasks li small{font-size:.8125rem;color:var(--muted);font-weight:600}.status-actions{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}.btn{min-height:40px;font-size:0.8125rem}.btn:focus-visible{outline:3px solid var(--accent);outline-offset:2px}@media(max-width:1050px){.metadata-live-status{grid-template-columns:1fr 1fr}.status-actions{justify-content:flex-start}}@media(max-width:700px){.metadata-live-status{grid-template-columns:1fr}.status-actions{grid-column:auto}}@media(prefers-reduced-motion:reduce){.progress-track span{transition:none}}
</style>
