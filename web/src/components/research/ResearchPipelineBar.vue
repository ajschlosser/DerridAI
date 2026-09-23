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
function shortPrompt(job:ResearchJob){const value=String(job.prompt||i18n.t("research.untitled_run")).replace(/\s+/g," ").trim();return value.length>72?`${value.slice(0,69)}…`:value}
function detail(job:ResearchJob){return researchJobDetail(job,(key,fallback)=>i18n.t(key,fallback),i18n.locale)}
</script>

<template>
  <section v-if="activeJobs.length" class="research-pipeline-bar" aria-labelledby="research-pipeline-bar-title">
    <div class="research-pipeline-bar-head">
      <div>
        <span class="research-live-dot" aria-hidden="true"></span>
        <div><b id="research-pipeline-bar-title">{{activeJobs.length}} {{i18n.t(activeJobs.length===1?'research.pipeline_running_one':'research.pipelines_running_many',activeJobs.length===1?'pipeline in progress':'pipelines in progress')}}</b><small>{{i18n.t('research.parallel_runs_help')}}</small></div>
      </div>
      <button class="research-text-action" type="button" @click="emit('openRuns')"><AppIcon name="history"/>{{i18n.t('research.view_all_runs')}}</button>
    </div>
    <div class="research-pipeline-scroll" role="list" :aria-label="i18n.t('research.active_pipelines')">
      <article v-for="job in activeJobs" :key="job.id" :class="['research-pipeline-chip',{selected:job.id===selectedJobId}]" role="listitem">
        <button class="research-pipeline-chip-main" type="button" @click="emit('select',job)">
          <span :class="['research-run-status-dot',job.status]" aria-hidden="true"></span>
          <span><b>{{shortPrompt(job)}}</b><small>{{detail(job)}}</small></span>
          <span class="research-run-status">{{statusLabel(job)}}</span>
        </button>
        <button v-if="canManage" class="research-pipeline-chip-cancel" type="button" :disabled="job.status==='cancelling'||job.cancel_requested" :aria-label="i18n.t('research.cancel_run')" @click="emit('cancel',job)">×</button>
      </article>
    </div>
  </section>
</template>

<style scoped>
.research-pipeline-bar {
  display: grid;
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: linear-gradient(180deg,var(--card),var(--card));
  box-shadow: 0 4px 16px rgba(35,50,70,.04);
}
.research-pipeline-bar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.research-pipeline-bar-head>div {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}
.research-pipeline-bar-head>div>div {
  display: grid;
  gap: 2px;
}
.research-pipeline-bar-head b {
  font-size: 0.78125rem;
  color: var(--text-2);
}
.research-pipeline-bar-head small {
  color: var(--muted);
  font-size: .8125rem;
  line-height: 1.45;
}
.research-live-dot {
  width: 9px;
  height: 9px;
  margin-top: 4px;
  border-radius: 50%;
  background: #d18b26;
  box-shadow: 0 0 0 5px rgba(209,139,38,.12);
  flex: 0 0 auto;
}
.research-pipeline-scroll {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 2px 1px 4px;
  scrollbar-width: thin;
}
.research-pipeline-chip-main {
  display: grid;
  grid-template-columns: 9px minmax(0,1fr) auto;
  align-items: center;
  gap: 9px;
  width: 100%;
  min-height: 58px;
  padding: 8px 40px 8px 10px;
  border: 0;
  background: transparent;
  text-align: left;
  color: var(--text-2);
  cursor: pointer;
}
.research-pipeline-chip-main:hover {
  background: var(--card);
}
.research-pipeline-chip-main:focus-visible,
.research-pipeline-chip-cancel:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: -2px;
}
.research-pipeline-chip-main>span:nth-child(2) {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.research-pipeline-chip-main b,
.research-pipeline-chip-main small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.research-pipeline-chip-main b {
  font-size: 0.78125rem;
}
.research-pipeline-chip-main small {
  font-size: .8125rem;
  color: var(--muted);
}
.research-pipeline-chip-cancel {
  position: absolute;
  right: 7px;
  top: 50%;
  translate: 0 -50%;
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--muted);
  font-size: 1.0625rem;
  cursor: pointer;
}
.research-pipeline-chip-cancel:hover {
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.research-pipeline-chip-cancel:disabled {
  opacity: .45;
  cursor: not-allowed;
}
@media (max-width:600px) {
  .research-pipeline-bar-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
@media (prefers-reduced-motion:reduce) {
  .research-live-dot {
    box-shadow: none;
  }
}
@media (prefers-reduced-motion:reduce) {
  .research-pipeline-scroll {
    scroll-behavior: auto;
  }
}
</style>
