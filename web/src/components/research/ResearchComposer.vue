<script setup lang="ts">
import { computed, ref } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { ResearchProfile, ResearchStore } from "../../types/research";

const props=withDefaults(defineProps<{
  prompt:string;
  instructions:string;
  sourceCollection:string;
  providerProfileId:string;
  responseLanguage:string;
  preset:string;
  evidenceCount:number;
  stores:ResearchStore[];
  profiles:ResearchProfile[];
  history:Array<Record<string,unknown>>;
  busy?:boolean;
  canRun?:boolean;
  canConfigure?:boolean;
  canManageRuns?:boolean;
  disabledReason?:string;
}>(),{busy:false,canRun:true,canConfigure:true,canManageRuns:true,disabledReason:""});
const emit=defineEmits<{
  "update:prompt":[value:string];
  "update:instructions":[value:string];
  "update:sourceCollection":[value:string];
  "update:providerProfileId":[value:string];
  "update:responseLanguage":[value:string];
  "update:preset":[value:string];
  run:[];
  settings:[];
  runs:[];
  history:[item:Record<string,unknown>];
}>();
const i18n=useI18nStore();
const historyOpen=ref(false);
const historyQuery=ref("");
const filteredHistory=computed(()=>{
  const needle=historyQuery.value.trim().toLocaleLowerCase();
  const rows=props.history.slice(0,40);
  if(!needle)return rows.slice(0,8);
  return rows.filter(item=>`${item.prompt||""} ${item.instructions||""}`.toLocaleLowerCase().includes(needle)).slice(0,12);
});
const selectedProfile=computed(()=>props.profiles.find(profile=>profile.id===props.providerProfileId));
const selectedStore=computed(()=>props.stores.find(store=>store.name===props.sourceCollection));
function historyLabel(item:Record<string,unknown>){
  const value=String(item.prompt||item.instructions||i18n.t("research.saved_prompt","Saved prompt")).replace(/\s+/g," ").trim();
  return value.length>92?`${value.slice(0,89)}…`:value;
}
function pickHistory(item:Record<string,unknown>){emit("history",item);historyOpen.value=false;historyQuery.value=""}
</script>

<template>
  <section class="research-composer-v031 card" aria-labelledby="research-compose-title">
    <header class="research-composer-heading">
      <div>
        <span class="section-label">{{i18n.t('nav.rag','Research')}}</span>
        <h2 id="research-compose-title">{{i18n.t('research.ask_title','What are you researching?')}}</h2>
        <p>{{i18n.t('research.ask_help','Ask a scholarly question. DerridAI will retrieve, rerank, synthesize, and bind the answer to inspectable evidence.')}}</p>
      </div>
      <div class="research-heading-actions">
        <button v-if="canManageRuns" class="btn" type="button" @click="emit('runs')"><AppIcon name="history"/>{{i18n.t('research.runs','Runs')}}</button>
        <button v-if="canConfigure" class="btn" type="button" @click="emit('settings')"><AppIcon name="gear"/>{{i18n.t('research.expert_settings','Expert settings')}}</button>
      </div>
    </header>

    <div class="research-question-shell">
      <label class="sr-only" for="researchQuestion">{{i18n.t('research.question','Research question')}}</label>
      <textarea id="researchQuestion" class="research-question-input" :value="prompt" :disabled="!canConfigure" :placeholder="i18n.t('research.question_placeholder','Ask about a concept, passage, relation, attribution, or disagreement…')" @input="emit('update:prompt',($event.target as HTMLTextAreaElement).value)"></textarea>
      <div class="research-question-tools">
        <div class="research-history-popover">
          <button class="research-text-action" type="button" :disabled="!canConfigure" :aria-expanded="historyOpen" aria-controls="researchHistoryMenu" @click="historyOpen=!historyOpen">
            <AppIcon name="history"/>{{i18n.t('research.recent_questions','Recent questions')}}
          </button>
          <div v-if="historyOpen" id="researchHistoryMenu" class="research-history-menu" role="dialog" :aria-label="i18n.t('research.recent_questions','Recent questions')">
            <label class="sr-only" for="researchHistorySearch">{{i18n.t('research.search_history','Search recent questions')}}</label>
            <input id="researchHistorySearch" v-model="historyQuery" class="control" type="search" :placeholder="i18n.t('research.search_history','Search recent questions')" autofocus>
            <div class="research-history-list">
              <button v-for="(item,index) in filteredHistory" :key="String(item.id||index)" type="button" @click="pickHistory(item)">
                <b>{{historyLabel(item)}}</b><small>{{String(item.timestamp||'')}}</small>
              </button>
              <p v-if="!filteredHistory.length" class="note">{{i18n.t('research.no_recent_questions','No matching recent questions.')}}</p>
            </div>
          </div>
        </div>
        <span>{{prompt.length.toLocaleString(i18n.locale)}} {{i18n.t('research.characters','characters')}}</span>
      </div>
    </div>

    <details class="research-instructions-disclosure">
      <summary>{{i18n.t('research.instructions','Additional instructions')}}<span>{{instructions?i18n.t('research.added','Added'):i18n.t('research.optional','Optional')}}</span></summary>
      <label class="sr-only" for="researchInstructions">{{i18n.t('research.instructions','Additional instructions')}}</label>
      <textarea id="researchInstructions" :value="instructions" :disabled="!canConfigure" :placeholder="i18n.t('research.instructions_placeholder','Optional constraints on framing, comparison, citation, or answer form.')" @input="emit('update:instructions',($event.target as HTMLTextAreaElement).value)"></textarea>
    </details>

    <fieldset class="research-compose-context" :disabled="!canConfigure">
      <legend class="sr-only">{{i18n.t('research.context','Research context')}}</legend>
      <label>
        <span>{{i18n.t('research.corpus','Corpus')}}</span>
        <select class="control" :value="sourceCollection" @change="emit('update:sourceCollection',($event.target as HTMLSelectElement).value)">
          <option v-for="store in stores" :key="store.name" :value="store.name">{{store.name}} · {{store.count.toLocaleString(i18n.locale)}}</option>
          <option v-if="!stores.length" value="">{{i18n.t('research.no_database','No corpus database')}}</option>
        </select>
        <small v-if="selectedStore">{{selectedStore.collection_role||'general'}}<template v-if="selectedStore.embedding_model"> · {{selectedStore.embedding_model}}</template></small>
      </label>
      <label>
        <span>{{i18n.t('research.profile','Research profile')}}</span>
        <select class="control" :value="providerProfileId" @change="emit('update:providerProfileId',($event.target as HTMLSelectElement).value)">
          <option v-for="profile in profiles" :key="profile.id" :value="profile.id">{{profile.name||profile.id}}</option>
        </select>
        <small>{{selectedProfile?.model||i18n.t('research.model_auto','Automatic model')}}</small>
      </label>
      <label>
        <span>{{i18n.t('research.retrieval_profile','Retrieval')}}</span>
        <select class="control" :value="preset" @change="emit('update:preset',($event.target as HTMLSelectElement).value)">
          <option value="balanced">{{i18n.t('research.preset_balanced','Balanced')}}</option>
          <option value="precision">{{i18n.t('research.preset_precision','High precision')}}</option>
          <option value="recall">{{i18n.t('research.preset_recall','High recall')}}</option>
          <option value="evidence" :disabled="evidenceCount===0">{{i18n.t('research.preset_evidence','Selected evidence only')}}</option>
          <option value="custom">{{i18n.t('research.preset_custom','Custom')}}</option>
        </select>
        <small>{{evidenceCount}} {{i18n.t('rag.selected_evidence','selected evidence')}}</small>
      </label>
      <label>
        <span>{{i18n.t('research.answer_language','Answer language')}}</span>
        <select class="control" :value="responseLanguage" @change="emit('update:responseLanguage',($event.target as HTMLSelectElement).value)">
          <option value="auto">{{i18n.t('research.language_auto','Automatic')}}</option>
          <option value="en">{{i18n.t('language.english_short','English')}}</option>
          <option value="fr">{{i18n.t('language.french_short','French')}}</option>
        </select>
        <small>{{i18n.t('research.language_help','Source-language routing remains independent.')}}</small>
      </label>
    </fieldset>

    <footer class="research-compose-footer">
      <div class="research-run-context-summary">
        <span><i></i>{{evidenceCount?`${evidenceCount} ${i18n.t('rag.selected_evidence','selected evidence')}`:i18n.t('research.retrieval_ready','Retrieval ready')}}</span>
        <span>{{selectedProfile?.name||selectedProfile?.id||i18n.t('research.no_profile','No profile')}}</span>
      </div>
      <span class="action-tooltip-wrap" :data-tooltip="!canRun?disabledReason:''">
        <button class="btn primary research-run-button" type="button" :disabled="busy||!canRun" :aria-disabled="busy||!canRun" @click="emit('run')">
          <AppIcon name="spark"/>{{busy?i18n.t('research.starting','Starting…'):i18n.t('research.run','Research')}}
        </button>
      </span>
    </footer>
  </section>
</template>

<style scoped>
.research-history-list {
  max-height: 300px;
  overflow: auto;
  display: grid;
  gap: 3px;
  margin-top: 7px;
}
.research-history-list button {
  width: 100%;
  display: grid;
  gap: 2px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  padding: 8px 9px;
  text-align: left;
  color: var(--text-2);
  cursor: pointer;
}
.research-history-list button:hover,
.research-history-list button:focus-visible {
  background: var(--soft);
  outline: 0;
}
.research-history-list b {
  font-size: 0.78125rem;
  font-weight: 680;
  line-height: 1.35;
}
.research-history-list small {
  font-size: .8125rem;
  color: var(--muted);
}
</style>
