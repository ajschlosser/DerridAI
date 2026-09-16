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
      <header class="research-drawer-head"><div><span class="section-label">{{i18n.t('research.runs','Runs')}}</span><h2 id="research-runs-title">{{i18n.t('research.research_history','Research history')}}</h2><p>{{active}} {{i18n.t('research.active_runs','active')}} · {{jobs.length}} {{i18n.t('research.retained_runs','retained')}}</p></div><div class="tools"><button class="btn" type="button" @click="emit('refresh')"><AppIcon name="refresh"/>{{i18n.t('ui.refresh','Refresh')}}</button><button class="btn icon-only" type="button" :aria-label="i18n.t('ui.close','Close')" @click="close">×</button></div></header>
      <div class="research-runs-content">
        <section v-if="selectedJob" class="research-run-inspector" aria-labelledby="research-run-inspector-title">
          <div class="research-run-inspector-head"><div><span class="section-label">{{i18n.t('research.current_run','Current run')}}</span><h3 id="research-run-inspector-title">{{selectedJob.prompt||i18n.t('research.untitled_run','Untitled research run')}}</h3><p>{{selectedJob.provider||''}}<template v-if="selectedJob.model"> · {{selectedJob.model}}</template><template v-if="selectedJob.source_collection"> · {{selectedJob.source_collection}}</template></p></div><span :class="['research-run-status',selectedJob.status]">{{statusLabel(selectedJob)}}</span></div>
          <div v-if="selectedJob.result?.stages?.length" class="research-stage-timeline">
            <div v-for="(stage,index) in selectedJob.result.stages" :key="`${stage.name||'stage'}-${index}`"><span>{{index+1}}</span><b>{{stageLabel(stage.name)}}</b><small>{{Number(stage.seconds||0).toFixed(3)}}s</small></div>
          </div>
          <details v-if="selectedJob.result?.query_metadata||selectedJob.result?.retrieval" class="research-run-diagnostics">
            <summary>{{i18n.t('research.retrieval_diagnostics','Retrieval diagnostics')}}</summary>
            <div><pre v-if="selectedJob.result?.query_metadata">{{JSON.stringify(selectedJob.result.query_metadata,null,2)}}</pre><pre v-if="selectedJob.result?.retrieval">{{JSON.stringify(selectedJob.result.retrieval,null,2)}}</pre></div>
          </details>
        </section>
        <div class="research-runs-list">
        <article v-for="job in jobs" :key="job.id" :class="['research-run-card',{selected:job.id===selectedJobId}]">
          <button class="research-run-card-main" type="button" @click="emit('open',job)">
            <span :class="['research-run-status-dot',job.status]"></span>
            <span class="research-run-card-copy"><b>{{job.prompt||i18n.t('research.untitled_run','Untitled research run')}}</b><small>{{job.source_collection||i18n.t('research.evidence_only','Evidence only')}} · {{job.model||job.provider||''}}</small><span>{{detail(job)}}<template v-if="job.finished_at||job.created_at"> · {{when(job.finished_at||job.created_at)}}</template></span></span>
            <span class="research-run-status">{{statusLabel(job)}}</span>
          </button>
          <div v-if="canManage" class="research-run-card-actions">
            <button v-if="['queued','running','cancelling'].includes(job.status)" class="research-text-action danger" type="button" :disabled="job.status==='cancelling'||job.cancel_requested" @click="emit('cancel',job)">{{job.cancel_requested?i18n.t('research.cancelling','Cancelling…'):i18n.t('ui.cancel','Cancel')}}</button>
            <button v-else class="research-text-action danger" type="button" @click="emit('remove',job)">{{i18n.t('ui.remove','Remove')}}</button>
          </div>
        </article>
          <div v-if="!jobs.length" class="research-evidence-empty"><span aria-hidden="true">∴</span><b>{{i18n.t('research.no_runs','No Research runs yet')}}</b><p>{{i18n.t('research.no_runs_help','Completed and active runs will appear here.')}}</p></div>
        </div>
      </div>
    </div>
  </dialog>
</template>
