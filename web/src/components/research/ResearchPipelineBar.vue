<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { ResearchJob } from "../../types/research";
import { researchJobDetail } from "./researchI18n";

const props=withDefaults(defineProps<{
  jobs?:ResearchJob[];
  selectedJobId?:string;
  canManage?:boolean;
}>(),{jobs:()=>[],selectedJobId:"",canManage:false});
const emit=defineEmits<{select:[job:ResearchJob];cancel:[job:ResearchJob];openRuns:[]}>();
const i18n=useI18nStore();
const activeJobs=computed(()=>props.jobs.filter(job=>["queued","running","cancelling"].includes(job.status)));
function statusLabel(job:ResearchJob){return i18n.t(`research.status_${job.status}`,job.status)}
function shortPrompt(job:ResearchJob){const value=String(job.prompt||i18n.t("research.untitled_run","Untitled research run")).replace(/\s+/g," ").trim();return value.length>72?`${value.slice(0,69)}…`:value}
function detail(job:ResearchJob){return researchJobDetail(job,(key,fallback)=>i18n.t(key,fallback),i18n.locale)}
</script>

<template>
  <section v-if="activeJobs.length" class="research-pipeline-bar" aria-labelledby="research-pipeline-bar-title">
    <div class="research-pipeline-bar-head">
      <div>
        <span class="research-live-dot" aria-hidden="true"></span>
        <div><b id="research-pipeline-bar-title">{{activeJobs.length}} {{i18n.t(activeJobs.length===1?'research.pipeline_running_one':'research.pipelines_running_many',activeJobs.length===1?'pipeline in progress':'pipelines in progress')}}</b><small>{{i18n.t('research.parallel_runs_help','Start another question at any time. Each run continues independently and provider concurrency limits determine when queued work executes.')}}</small></div>
      </div>
      <button class="research-text-action" type="button" @click="emit('openRuns')"><AppIcon name="history"/>{{i18n.t('research.view_all_runs','View all runs')}}</button>
    </div>
    <div class="research-pipeline-scroll" role="list" :aria-label="i18n.t('research.active_pipelines','Active research pipelines')">
      <article v-for="job in activeJobs" :key="job.id" :class="['research-pipeline-chip',{selected:job.id===selectedJobId}]" role="listitem">
        <button class="research-pipeline-chip-main" type="button" @click="emit('select',job)">
          <span :class="['research-run-status-dot',job.status]" aria-hidden="true"></span>
          <span><b>{{shortPrompt(job)}}</b><small>{{detail(job)}}</small></span>
          <span class="research-run-status">{{statusLabel(job)}}</span>
        </button>
        <button v-if="canManage" class="research-pipeline-chip-cancel" type="button" :disabled="job.status==='cancelling'||job.cancel_requested" :aria-label="i18n.t('research.cancel_run','Cancel research run')" @click="emit('cancel',job)">×</button>
      </article>
    </div>
  </section>
</template>
