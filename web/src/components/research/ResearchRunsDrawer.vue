<script setup lang="ts">
import { computed, ref } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { ResearchJob } from "../../types/research";
import { researchJobDetail, researchStageLabel } from "./researchI18n";
const props=withDefaults(defineProps<{jobs?:ResearchJob[];selectedJobId?:string;selectedJob?:ResearchJob|null;canManage?:boolean}>(),{jobs:()=>[],selectedJobId:"",selectedJob:null,canManage:false});
const emit=defineEmits<{open:[job:ResearchJob];cancel:[job:ResearchJob];remove:[job:ResearchJob];refresh:[]}>();
const i18n=useI18nStore();
const dialog=ref<HTMLDialogElement|null>(null);
const active=computed(()=>props.jobs.filter(job=>["queued","running","cancelling"].includes(job.status)).length);
function open(){dialog.value?.showModal()}
function close(){dialog.value?.close()}
function when(value?:string|null){if(!value)return "";const date=new Date(value);return Number.isFinite(date.getTime())?date.toLocaleString(i18n.locale):String(value)}
function statusLabel(job:ResearchJob){return i18n.t(`research.status_${job.status}`,job.status)}
function detail(job:ResearchJob){return researchJobDetail(job,(key,fallback)=>i18n.t(key,fallback),i18n.locale)}
function stageLabel(stage:unknown){return researchStageLabel(stage,(key,fallback)=>i18n.t(key,fallback),i18n.locale)}
defineExpose({open,close});
</script>
<template>
  <dialog ref="dialog" class="research-drawer research-runs-dialog" aria-labelledby="research-runs-title" @cancel.prevent="close">
    <div class="research-drawer-shell">
      <header class="research-drawer-head"><div><span class="section-label">{{i18n.t('research.runs')}}</span><h2 id="research-runs-title">{{i18n.t('research.research_history')}}</h2><p>{{active}} {{i18n.t('research.active_runs')}} · {{jobs.length}} {{i18n.t('research.retained_runs')}}</p></div><div class="tools"><button class="btn" type="button" @click="emit('refresh')"><AppIcon name="refresh"/>{{i18n.t('ui.refresh')}}</button><button class="btn icon-only" type="button" :aria-label="i18n.t('ui.close')" @click="close">×</button></div></header>
      <div class="research-runs-content">
        <section v-if="selectedJob" class="research-run-inspector" aria-labelledby="research-run-inspector-title">
          <div class="research-run-inspector-head"><div><span class="section-label">{{i18n.t('research.current_run')}}</span><h3 id="research-run-inspector-title">{{selectedJob.prompt||i18n.t('research.untitled_run')}}</h3><p>{{selectedJob.provider||''}}<template v-if="selectedJob.model"> · {{selectedJob.model}}</template><template v-if="selectedJob.source_collection"> · {{selectedJob.source_collection}}</template></p></div><span :class="['research-run-status',selectedJob.status]">{{statusLabel(selectedJob)}}</span></div>
          <div v-if="selectedJob.result?.stages?.length" class="research-stage-timeline">
            <div v-for="(stage,index) in selectedJob.result.stages" :key="`${stage.name||'stage'}-${index}`"><span>{{index+1}}</span><b>{{stageLabel(stage.name)}}</b><small>{{Number(stage.seconds||0).toFixed(3)}}s</small></div>
          </div>
          <details v-if="selectedJob.result?.query_metadata||selectedJob.result?.retrieval" class="research-run-diagnostics">
            <summary>{{i18n.t('research.retrieval_diagnostics')}}</summary>
            <div><pre v-if="selectedJob.result?.query_metadata">{{JSON.stringify(selectedJob.result.query_metadata,null,2)}}</pre><pre v-if="selectedJob.result?.retrieval">{{JSON.stringify(selectedJob.result.retrieval,null,2)}}</pre></div>
          </details>
        </section>
        <div class="research-runs-list">
        <article v-for="job in jobs" :key="job.id" :class="['research-run-card',{selected:job.id===selectedJobId}]">
          <button class="research-run-card-main" type="button" @click="emit('open',job)">
            <span :class="['research-run-status-dot',job.status]"></span>
            <span class="research-run-card-copy"><b>{{job.prompt||i18n.t('research.untitled_run')}}</b><small>{{job.source_collection||i18n.t('research.evidence_only')}} · {{job.model||job.provider||''}}</small><span>{{detail(job)}}<template v-if="job.finished_at||job.created_at"> · {{when(job.finished_at||job.created_at)}}</template></span></span>
            <span class="research-run-status">{{statusLabel(job)}}</span>
          </button>
          <div v-if="canManage" class="research-run-card-actions">
            <button v-if="['queued','running','cancelling'].includes(job.status)" class="research-text-action danger" type="button" :disabled="job.status==='cancelling'||job.cancel_requested" @click="emit('cancel',job)">{{job.cancel_requested?i18n.t('research.cancelling'):i18n.t('ui.cancel')}}</button>
            <button v-else class="research-text-action danger" type="button" @click="emit('remove',job)">{{i18n.t('ui.remove')}}</button>
          </div>
        </article>
          <div v-if="!jobs.length" class="research-evidence-empty"><span aria-hidden="true">∴</span><b>{{i18n.t('research.no_runs')}}</b><p>{{i18n.t('research.no_runs_help')}}</p></div>
        </div>
      </div>
    </div>
  </dialog>
</template>

<style scoped>
.research-run-card-main {
  width: 100%;
  min-height: 70px;
  display: grid;
  grid-template-columns: 10px minmax(0,1fr) auto;
  gap: 10px;
  align-items: center;
  border: 0;
  border-radius: 8px;
  background: transparent;
  padding: 8px;
  text-align: left;
  color: var(--text-2);
  cursor: pointer;
}
.research-run-card-main:hover {
  background: var(--card);
}
.research-run-card-main:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
}
.research-run-card-copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.research-run-card-copy b {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.78125rem;
}
.research-run-card-copy small,
.research-run-card-copy>span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--muted);
  font-size: .8125rem;
}
.research-run-card-actions {
  display: flex;
  justify-content: flex-end;
  padding: 0 8px 6px;
}
@media (max-width:560px) {
  .research-run-card-main {
    grid-template-columns: 10px minmax(0,1fr);
  }
}
.research-run-inspector {
  display: grid;
  gap: 12px;
  margin: 12px 12px 4px;
  padding: 13px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
}
.research-run-inspector-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}
.research-run-inspector-head h3 {
  margin: 2px 0 3px;
  font-size: 0.875rem;
  line-height: 1.4;
  color: var(--text-2);
}
.research-run-inspector-head p {
  margin: 0;
  color: var(--muted);
  font-size: .8125rem;
}
.research-stage-timeline {
  display: grid;
  grid-template-columns: repeat(auto-fit,minmax(112px,1fr));
  gap: 6px;
}
.research-stage-timeline>div {
  display: grid;
  grid-template-columns: 24px minmax(0,1fr);
  grid-template-rows: auto auto;
  gap: 1px 6px;
  align-items: center;
  padding: 7px;
  border-radius: 7px;
  background: var(--card);
  border: 1px solid var(--line);
}
.research-stage-timeline>div>span {
  grid-row: 1/3;
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--ui-accent-soft);
  color: var(--accent-fg);
  font-size: .8125rem;
  font-weight: 800;
}
.research-stage-timeline b {
  font-size: .8125rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.research-stage-timeline small {
  font-size: .8125rem;
  color: var(--muted);
}
.research-run-diagnostics {
  border-top: 1px solid var(--line);
  padding-top: 8px;
}
.research-run-diagnostics>summary {
  cursor: pointer;
  color: var(--text-2);
  font-size: .8125rem;
  font-weight: 700;
}
.research-run-diagnostics>summary:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  border-radius: 5px;
}
.research-run-diagnostics>div {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 7px;
  margin-top: 7px;
}
.research-run-diagnostics pre {
  max-height: 230px;
  overflow: auto;
  margin: 0;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--card);
  color: var(--text-2);
  font: 12px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
@media (max-width:560px) {
  .research-run-diagnostics>div {
    grid-template-columns: 1fr;
  }
}
</style>
