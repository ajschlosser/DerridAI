<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { CorpusBuild } from "../api/pdfCorpus";

const props=defineProps<{build:CorpusBuild;disabled?:boolean}>();
const emit=defineEmits<{settle:[];cancel:[]}>();
const i18n=useI18nStore();
const total=computed(()=>Number(props.build.metadata_tasks_total||Math.max(0,Number(props.build.metadata_enrichment_total||props.build.record_count||0)*3)));
const complete=computed(()=>Number(props.build.metadata_tasks_completed||0));
const failed=computed(()=>Number(props.build.metadata_tasks_failed||0));
const skipped=computed(()=>Number(props.build.metadata_tasks_skipped||0));
const running=computed(()=>Number(props.build.metadata_tasks_running||0));
const queued=computed(()=>Number(props.build.metadata_tasks_queued||Math.max(0,total.value-complete.value-failed.value-skipped.value-running.value)));
const active=computed(()=>Array.isArray(props.build.metadata_active_tasks)?props.build.metadata_active_tasks:[]);
const settled=computed(()=>complete.value+failed.value+skipped.value);
const lastProgress=computed(()=>props.build.metadata_last_progress_at?new Date(props.build.metadata_last_progress_at).toLocaleTimeString():i18n.t("pdf_corpus.not_yet","not yet"));
function elapsedSince(value?:string|null):number{if(!value)return 0;const ms=Date.now()-new Date(value).getTime();return Number.isFinite(ms)&&ms>0?ms:0}
function formatDuration(ms:number):string{const totalSeconds=Math.max(0,Math.round(ms/1000));const minutes=Math.floor(totalSeconds/60);const seconds=totalSeconds%60;return minutes?`${minutes}m ${String(seconds).padStart(2,"0")}s`:`${seconds}s`}
const elapsed=computed(()=>formatDuration(elapsedSince(props.build.metadata_started_at)));
const eta=computed(()=>{
  const elapsedMs=elapsedSince(props.build.metadata_started_at);
  if(!elapsedMs||settled.value<=0||settled.value>=total.value)return "";
  const remaining=Math.max(0,total.value-settled.value);
  return formatDuration((elapsedMs/settled.value)*remaining);
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
        <strong class="status-count">{{settled}} / {{total}} <small>{{i18n.t('pdf_corpus.metadata_tasks_unit','tasks')}}</small></strong>
      </div>
      <p>{{i18n.tf('pdf_corpus.metadata_live_summary','{complete} complete · {running} active · {queued} queued · {failed} need review',{complete,running,queued,failed:failed+skipped})}}</p>
      <p class="status-secondary">{{i18n.t('pdf_corpus.elapsed','Elapsed')}}: {{elapsed}}<template v-if="eta"> · {{i18n.t('pdf_corpus.eta','ETA')}}: ~{{eta}}</template> · {{i18n.t('pdf_corpus.last_progress','Last settled task')}}: {{lastProgress}} · {{i18n.t('pdf_corpus.concurrency','Concurrency')}}: {{build.metadata_concurrency||1}}</p>
      <p class="saved-indicator">✓ {{i18n.t('pdf_corpus.resume_safe','Resume-safe')}} · {{i18n.t('pdf_corpus.saved_checkpoint','checkpoint saved')}} {{lastProgress}}</p>
      <div class="progress-track" :aria-label="i18n.t('pdf_corpus.metadata_task_progress','Metadata task progress')" :aria-valuenow="settled" :aria-valuemin="0" :aria-valuemax="Math.max(1,total)" role="progressbar"><span :style="{width:`${total?Math.min(100,(settled/total)*100):0}%`}"></span></div>
    </div>

    <div v-if="active.length" class="active-tasks" :aria-label="i18n.t('pdf_corpus.active_metadata_tasks','Active metadata tasks')">
      <b>{{i18n.t('pdf_corpus.active_now','Active now')}}</b>
      <ul><li v-for="item in active.slice(0,6)" :key="`${item.record_id}-${item.task}`"><span>{{item.record_id}}</span><strong>{{taskLabel(String(item.task||''))}}<small v-if="activeElapsed(item.started_at)"> · {{activeElapsed(item.started_at)}}</small></strong></li></ul>
    </div>

    <div class="status-actions">
      <button type="button" class="btn" :disabled="disabled||Boolean(build.metadata_settle_requested)" @click="emit('settle')">{{build.metadata_settle_requested?i18n.t('pdf_corpus.settle_requested','Settling remaining tasks…'):i18n.t('pdf_corpus.continue_unresolved','Continue with unresolved metadata')}}</button>
      <button type="button" class="btn" :disabled="disabled" @click="emit('cancel')">{{i18n.t('pdf_corpus.cancel_build','Cancel build')}}</button>
    </div>
  </section>
</template>

<style scoped>
.metadata-live-status{display:grid;grid-template-columns:minmax(0,1fr) minmax(240px,.55fr) auto;gap:18px;align-items:center;padding:16px 18px;border:1px solid var(--line);border-radius:12px;background:var(--card)}
.metadata-live-status[data-stalled="true"]{border-color:var(--tone-warn-border);background:var(--tone-warn-bg)}.status-main{display:grid;gap:7px;min-width:0}.status-title-row{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}.eyebrow{font-size:.8125rem;line-height:1.35;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:800}.status-title-row h2{margin:2px 0 0;font-size:1.0625rem;line-height:1.3}.status-count{font-size:1.125rem;white-space:nowrap}.status-main p{margin:0;font-size:0.8125rem;line-height:1.45}.status-secondary{color:var(--muted)}.saved-indicator{width:max-content;max-width:100%;padding:3px 7px;border-radius:999px;background:var(--tone-ok-bg);color:var(--accent-fg)!important;font-size:.8125rem!important;font-weight:750}.progress-track{height:8px;overflow:hidden;border-radius:999px;background:var(--soft)}.progress-track span{display:block;height:100%;background:var(--accent);transition:width .2s ease}.active-tasks{display:grid;gap:7px;min-width:0}.active-tasks>b{font-size:0.8125rem}.active-tasks ul{list-style:none;margin:0;padding:0;display:grid;gap:4px}.active-tasks li{display:flex;justify-content:space-between;gap:10px;font-size:.8125rem;line-height:1.4}.active-tasks li span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--muted)}.active-tasks li strong{white-space:nowrap}.active-tasks li small{font-size:.8125rem;color:var(--muted);font-weight:600}.status-actions{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}.btn{min-height:40px;font-size:0.8125rem}.btn:focus-visible{outline:3px solid var(--accent);outline-offset:2px}@media(max-width:1050px){.metadata-live-status{grid-template-columns:1fr 1fr}.status-actions{grid-column:1/-1;justify-content:flex-start}}@media(max-width:700px){.metadata-live-status{grid-template-columns:1fr}.status-actions{grid-column:auto}}@media(prefers-reduced-motion:reduce){.progress-track span{transition:none}}
</style>
