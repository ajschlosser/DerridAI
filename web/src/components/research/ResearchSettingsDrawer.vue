<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { ResearchConfig, ResearchProfile } from "../../types/research";

type SettingsSection="retrieval"|"evidence"|"generation";
const props=defineProps<{
  config:ResearchConfig;
  profiles:ResearchProfile[];
  selectedProfileId:string;
  generation:Record<string,unknown>;
  model:string;
  models:string[];
  researcher:boolean;
}>();
const emit=defineEmits<{apply:[payload:{config:Partial<ResearchConfig>;generation:Record<string,unknown>;model:string}];discover:[]} >();
const i18n=useI18nStore();
const dialog=ref<HTMLDialogElement|null>(null);
const activeSection=ref<SettingsSection>("retrieval");
const draft=ref<Partial<ResearchConfig>>({});
const generationDraft=ref<Record<string,unknown>>({});
const modelDraft=ref("");
const extraOptions=ref("{}");
const settingsError=ref("");
const selectedProfile=computed(()=>props.profiles.find(profile=>profile.id===props.selectedProfileId)||null);
const activeSectionTitle=computed(()=>({
  retrieval:i18n.t("research.retrieval","Retrieval"),
  evidence:i18n.t("research.evidence_citations","Evidence & citations"),
  generation:i18n.t("research.generation","Generation"),
})[activeSection.value]);

function sync(){
  settingsError.value="";
  draft.value={
    locales:[...(props.config.locales||[])],search_types:[...(props.config.search_types||[])],
    k:props.config.k,fetch_k:props.config.fetch_k,lambda_mult:props.config.lambda_mult,rrf_k:props.config.rrf_k,
    rerank_top_n:props.config.rerank_top_n,reranker:props.config.reranker,cross_encoder_model:props.config.cross_encoder_model,
    query_decomposition:props.config.query_decomposition,query_decomposition_num_predict:props.config.query_decomposition_num_predict,
    evidence_record_char_limit:props.config.evidence_record_char_limit,evidence_total_char_limit:props.config.evidence_total_char_limit,
    bind_citations:props.config.bind_citations,include_works_cited:props.config.include_works_cited,auto_grade:props.config.auto_grade,
    auto_grade_provider_profile_id:props.config.auto_grade_provider_profile_id,
  };
  generationDraft.value={...props.generation};
  modelDraft.value=props.model||"";
  const raw=props.generation.extra_options;
  extraOptions.value=typeof raw==="string"?raw:JSON.stringify(raw||{},null,2);
}
function open(){sync();activeSection.value="retrieval";dialog.value?.showModal();void nextTick(()=>dialog.value?.querySelector<HTMLElement>('[data-settings-tab="retrieval"]')?.focus())}
function close(){dialog.value?.close()}
function toggleList(key:"locales"|"search_types",value:string,checked:boolean){
  const list=new Set((draft.value[key] as string[]|undefined)||[]);checked?list.add(value):list.delete(value);draft.value[key]=[...list];
}
function resetSection(section:SettingsSection){
  const source=props.config;
  if(section==="retrieval")Object.assign(draft.value,{locales:[...(source.locales||[])],search_types:[...(source.search_types||[])],k:source.k,fetch_k:source.fetch_k,lambda_mult:source.lambda_mult,rrf_k:source.rrf_k,rerank_top_n:source.rerank_top_n,reranker:source.reranker,cross_encoder_model:source.cross_encoder_model,query_decomposition:source.query_decomposition,query_decomposition_num_predict:source.query_decomposition_num_predict});
  else if(section==="evidence")Object.assign(draft.value,{evidence_record_char_limit:source.evidence_record_char_limit,evidence_total_char_limit:source.evidence_total_char_limit,bind_citations:source.bind_citations,include_works_cited:source.include_works_cited,auto_grade:source.auto_grade,auto_grade_provider_profile_id:source.auto_grade_provider_profile_id});
  else{generationDraft.value={...props.generation};modelDraft.value=props.model||"";const raw=props.generation.extra_options;extraOptions.value=typeof raw==="string"?raw:JSON.stringify(raw||{},null,2)}
}
function apply(){
  try{
    const parsed=JSON.parse(extraOptions.value||"{}");
    if(!parsed||Array.isArray(parsed)||typeof parsed!=="object")throw new Error();
    generationDraft.value={...generationDraft.value,extra_options:parsed};
  }catch{settingsError.value=i18n.t("research.invalid_provider_options","Provider options must be a valid JSON object.");activeSection.value="generation";return}
  settingsError.value="";
  emit("apply",{config:draft.value,generation:generationDraft.value,model:modelDraft.value.trim()});close();
}
watch(()=>props.selectedProfileId,()=>{if(dialog.value?.open)sync()});
defineExpose({open,close});
</script>

<template>
  <dialog ref="dialog" class="research-settings-dialog research-settings-studio-dialog" aria-labelledby="research-settings-title" @cancel.prevent="close">
    <div class="research-settings-studio-shell">
      <header class="research-settings-studio-head">
        <div>
          <span class="section-label">{{i18n.t('research.expert_settings','Expert settings')}}</span>
          <h2 id="research-settings-title">{{i18n.t('research.pipeline_options','Retrieval, evidence & generation')}}</h2>
          <p>{{i18n.t('research.expert_help','These settings are for reproducibility, evaluation, and unusual research tasks. Normal research should not require them.')}}</p>
        </div>
        <div class="research-settings-studio-head-actions">
          <span class="research-settings-profile-pill"><AppIcon name="spark"/><span><small>{{i18n.t('research.profile','Research profile')}}</small><b>{{selectedProfile?.name||selectedProfile?.id||i18n.t('research.no_profile','No profile')}}</b></span></span>
          <button class="btn icon-only" type="button" :aria-label="i18n.t('ui.close','Close')" @click="close">×</button>
        </div>
      </header>

      <div class="research-settings-studio-body">
        <nav class="research-settings-nav" :aria-label="i18n.t('research.expert_sections','Expert settings sections')">
          <button data-settings-tab="retrieval" type="button" :class="{active:activeSection==='retrieval'}" :aria-current="activeSection==='retrieval'?'page':undefined" @click="activeSection='retrieval'">
            <AppIcon name="search"/><span><b>{{i18n.t('research.retrieval','Retrieval')}}</b><small>{{i18n.t('research.retrieval_nav_help','Routing, candidate depth and reranking')}}</small></span>
          </button>
          <button data-settings-tab="evidence" type="button" :class="{active:activeSection==='evidence'}" :aria-current="activeSection==='evidence'?'page':undefined" @click="activeSection='evidence'">
            <AppIcon name="record"/><span><b>{{i18n.t('research.evidence_citations','Evidence & citations')}}</b><small>{{i18n.t('research.evidence_nav_help','Context budget, source binding and grading')}}</small></span>
          </button>
          <button data-settings-tab="generation" type="button" :class="{active:activeSection==='generation'}" :aria-current="activeSection==='generation'?'page':undefined" @click="activeSection='generation'">
            <AppIcon name="spark"/><span><b>{{i18n.t('research.generation','Generation')}}</b><small>{{i18n.t('research.generation_nav_help','Model and per-run inference controls')}}</small></span>
          </button>
          <div class="research-settings-nav-note"><AppIcon name="history"/><p>{{i18n.t('research.settings_reproducibility_note','These values are stored with each run so an analysis can be reproduced later.')}}</p></div>
        </nav>

        <main class="research-settings-panel" :aria-label="activeSectionTitle">
          <section v-show="activeSection==='retrieval'" class="research-settings-page" aria-labelledby="research-settings-retrieval-title">
            <div class="research-settings-page-head"><div><span class="section-label">01</span><h3 id="research-settings-retrieval-title">{{i18n.t('research.retrieval','Retrieval')}}</h3><p>{{i18n.t('research.retrieval_expert_help','Tune recall, rank fusion, reranking, and multilingual query routing.')}}</p></div><button class="research-text-action" type="button" @click="resetSection('retrieval')"><AppIcon name="refresh"/>{{i18n.t('research.reset_section','Reset section')}}</button></div>
            <div class="research-settings-card-grid">
              <fieldset class="research-settings-card">
                <legend>{{i18n.t('research.routing','Routing')}}</legend>
                <p>{{i18n.t('research.routing_help','Choose which document languages and retrieval strategies participate in candidate discovery.')}}</p>
                <div class="research-settings-choice-row"><span>{{i18n.t('research.document_languages','Document languages')}}</span><div class="research-segmented-checks"><label v-for="code in ['en','fr']" :key="code"><input type="checkbox" :checked="(draft.locales||[]).includes(code)" @change="toggleList('locales',code,($event.target as HTMLInputElement).checked)"><span>{{code==='en'?i18n.t('language.english_short','English'):i18n.t('language.french_short','French')}}</span></label></div></div>
                <div class="research-settings-choice-row"><span>{{i18n.t('research.retrieval_routes','Retrieval routes')}}</span><div class="research-segmented-checks"><label v-for="route in [['mmr','MMR'],['similarity',i18n.t('research.similarity','Similarity')]]" :key="String(route[0])"><input type="checkbox" :checked="(draft.search_types||[]).includes(String(route[0]))" @change="toggleList('search_types',String(route[0]),($event.target as HTMLInputElement).checked)"><span>{{route[1]}}</span></label></div></div>
              </fieldset>

              <fieldset class="research-settings-card">
                <legend>{{i18n.t('research.candidate_pool','Candidate pool')}}</legend>
                <p>{{i18n.t('research.candidate_pool_help','Control how broadly DerridAI searches before fusion and reranking.')}}</p>
                <div class="research-settings-grid compact">
                  <label><span><code>k</code>{{i18n.t('research.k_label','Candidates retained')}}</span><input v-model.number="draft.k" class="control" type="number" min="1" max="500"><small>{{i18n.t('research.k_help','Candidates retained per retrieval route')}}</small></label>
                  <label><span><code>fetch_k</code>{{i18n.t('research.fetch_k_label','MMR candidate pool')}}</span><input v-model.number="draft.fetch_k" class="control" type="number" min="1" max="5000"><small>{{i18n.t('research.fetch_k_help','MMR candidate pool')}}</small></label>
                  <label><span><code>MMR λ</code>{{i18n.t('research.lambda_label','Relevance balance')}}</span><input v-model.number="draft.lambda_mult" class="control" type="number" step="0.05" min="0" max="1"><small>{{i18n.t('research.lambda_help','Relevance vs. diversity')}}</small></label>
                  <label><span><code>RRF k</code>{{i18n.t('research.rrf_label','Fusion smoothing')}}</span><input v-model.number="draft.rrf_k" class="control" type="number" min="1"><small>{{i18n.t('research.rrf_help','Rank-fusion smoothing constant')}}</small></label>
                </div>
              </fieldset>

              <fieldset class="research-settings-card wide">
                <legend>{{i18n.t('research.reranking_decomposition','Reranking & query decomposition')}}</legend>
                <p>{{i18n.t('research.reranking_decomposition_help','Refine the fused candidate set and optionally expand the question into multilingual subqueries.')}}</p>
                <div class="research-settings-grid three">
                  <label><span>{{i18n.t('research.rerank_top_n','Rerank top N')}}</span><input v-model.number="draft.rerank_top_n" class="control" type="number" min="1" max="500"></label>
                  <label><span>{{i18n.t('research.reranker','Reranker')}}</span><select v-model="draft.reranker" class="control"><option value="cross_encoder">{{i18n.t('research.cross_encoder','Cross-encoder')}}</option><option value="lexical">{{i18n.t('research.lexical_fallback','Lexical/vector fallback')}}</option><option value="none">{{i18n.t('research.none','None')}}</option></select></label>
                  <label><span>{{i18n.t('research.decomposition_tokens','Query-decomposition tokens')}}</span><input v-model.number="draft.query_decomposition_num_predict" class="control" type="number" min="64" max="8192"></label>
                  <label class="wide"><span>{{i18n.t('research.cross_encoder_model','Cross-encoder model')}}</span><input v-model="draft.cross_encoder_model" class="control"></label>
                  <label class="research-toggle-setting wide"><input v-model="draft.query_decomposition" type="checkbox"><span><b>{{i18n.t('research.query_decomposition','Query decomposition')}}</b><small>{{i18n.t('research.query_decomposition_help','Generate subqueries and French formulations before retrieval.')}}</small></span></label>
                </div>
              </fieldset>
            </div>
          </section>

          <section v-show="activeSection==='evidence'" class="research-settings-page" aria-labelledby="research-settings-evidence-title">
            <div class="research-settings-page-head"><div><span class="section-label">02</span><h3 id="research-settings-evidence-title">{{i18n.t('research.evidence_citations','Evidence & citations')}}</h3><p>{{i18n.t('research.evidence_citations_help','Control evidence packet size and deterministic source binding.')}}</p></div><button class="research-text-action" type="button" @click="resetSection('evidence')"><AppIcon name="refresh"/>{{i18n.t('research.reset_section','Reset section')}}</button></div>
            <div class="research-settings-card-grid">
              <fieldset class="research-settings-card wide">
                <legend>{{i18n.t('research.evidence_budget','Evidence budget')}}</legend>
                <p>{{i18n.t('research.evidence_budget_help','Set an upper bound for each passage and for the full evidence packet sent to generation.')}}</p>
                <div class="research-settings-grid two">
                  <label><span>{{i18n.t('research.record_char_limit','Chars / evidence record')}}</span><input v-model.number="draft.evidence_record_char_limit" class="control" type="number" min="500" max="100000"><small>{{Number(draft.evidence_record_char_limit||0).toLocaleString(i18n.locale)}} {{i18n.t('research.characters','characters')}}</small></label>
                  <label><span>{{i18n.t('research.total_char_limit','Total evidence chars')}}</span><input v-model.number="draft.evidence_total_char_limit" class="control" type="number" min="5000" max="1000000"><small>{{Number(draft.evidence_total_char_limit||0).toLocaleString(i18n.locale)}} {{i18n.t('research.characters','characters')}}</small></label>
                </div>
              </fieldset>
              <fieldset class="research-settings-card">
                <legend>{{i18n.t('research.source_binding','Source binding')}}</legend>
                <p>{{i18n.t('research.source_binding_help','Keep generated claims auditable against deterministic evidence identifiers and citations.')}}</p>
                <div class="research-settings-stack">
                  <label class="research-toggle-setting"><input v-model="draft.bind_citations" type="checkbox"><span><b>{{i18n.t('research.bind_citations','Bind evidence tags to citations')}}</b><small>{{i18n.t('research.bind_citations_help','Validate evidence identifiers before final source formatting.')}}</small></span></label>
                  <label class="research-toggle-setting"><input v-model="draft.include_works_cited" type="checkbox"><span><b>{{i18n.t('research.include_works_cited','Append Works Cited')}}</b><small>{{i18n.t('research.works_cited_help','Add a deterministic bibliography after the answer.')}}</small></span></label>
                </div>
              </fieldset>
              <fieldset class="research-settings-card">
                <legend>{{i18n.t('research.evaluation','Evaluation')}}</legend>
                <p>{{i18n.t('research.evaluation_help','Optionally grade the final response after generation without blocking the main Research workspace.')}}</p>
                <div class="research-settings-stack">
                  <label class="research-toggle-setting"><input v-model="draft.auto_grade" type="checkbox"><span><b>{{i18n.t('research.auto_grade','Auto-grade final response')}}</b><small>{{i18n.t('research.auto_grade_help','Runs as the final background-pipeline step.')}}</small></span></label>
                  <label v-if="draft.auto_grade"><span>{{i18n.t('research.grading_profile','Grading profile')}}</span><select v-model="draft.auto_grade_provider_profile_id" class="control"><option v-for="profile in profiles" :key="profile.id" :value="profile.id">{{profile.name||profile.id}} · {{profile.model||i18n.t('research.model_auto','Automatic model')}}</option></select></label>
                </div>
              </fieldset>
            </div>
          </section>

          <section v-show="activeSection==='generation'" class="research-settings-page" aria-labelledby="research-settings-generation-title">
            <div class="research-settings-page-head"><div><span class="section-label">03</span><h3 id="research-settings-generation-title">{{i18n.t('research.generation','Generation')}}</h3><p>{{researcher?i18n.t('research.researcher_profile_locked','Generation settings are fixed by the administrator-approved Research profile.'):i18n.t('research.generation_override_help','Optional per-run overrides; the saved provider profile is not changed.')}}</p></div><div class="research-settings-page-actions"><button class="research-text-action" type="button" @click="resetSection('generation')"><AppIcon name="refresh"/>{{i18n.t('research.reset_section','Reset section')}}</button><button v-if="!researcher" class="btn" type="button" @click="emit('discover')"><AppIcon name="search"/>{{i18n.t('research.discover_models','Discover models')}}</button></div></div>
            <fieldset :disabled="researcher" class="research-settings-generation-fieldset">
              <div class="research-generation-model-card">
                <div><span class="section-label">{{i18n.t('research.active_profile','Active profile')}}</span><b>{{selectedProfile?.name||selectedProfile?.id||i18n.t('research.no_profile','No profile')}}</b><small>{{selectedProfile?.type==='openai'?i18n.t('providers.openai_compatible','OpenAI-compatible'):i18n.t('providers.ollama','Ollama')}}<template v-if="selectedProfile?.max_concurrent_requests"> · {{selectedProfile.max_concurrent_requests}} {{i18n.t('research.concurrent_requests','concurrent requests')}}</template></small></div>
                <label><span>{{i18n.t('research.model','Model')}}</span><input v-model="modelDraft" class="control" list="researchSettingsModels" autocomplete="off"><datalist id="researchSettingsModels"><option v-for="name in models" :key="name" :value="name"></option></datalist></label>
              </div>
              <div class="research-settings-card wide generation-parameters">
                <div class="research-settings-section-head"><div><b>{{i18n.t('research.inference_parameters','Inference parameters')}}</b><small>{{i18n.t('research.inference_parameters_help','Per-run model controls. Leave profile defaults unchanged unless the research task requires a reproducible override.')}}</small></div></div>
                <div class="research-settings-grid three">
                  <label><span><code>num_ctx</code>{{i18n.t('research.context_window','Context window')}}</span><input v-model.number="generationDraft.num_ctx" class="control" type="number" min="512"></label>
                  <label><span><code>num_predict</code>{{i18n.t('research.max_output_tokens','Maximum output')}}</span><input v-model.number="generationDraft.num_predict" class="control" type="number" min="16"></label>
                  <label><span>{{i18n.t('research.thinking','Thinking')}}</span><select v-model="generationDraft.think" class="control"><option value="false">{{i18n.t('research.off','Off')}}</option><option value="true">{{i18n.t('research.on','On')}}</option><option value="low">{{i18n.t('research.thinking_low','Low')}}</option><option value="medium">{{i18n.t('research.thinking_medium','Medium')}}</option><option value="high">{{i18n.t('research.thinking_high','High')}}</option></select></label>
                  <label><span>{{i18n.t('research.temperature','Temperature')}}</span><input v-model.number="generationDraft.temperature" class="control" type="number" step="0.01" min="0" max="2"></label>
                  <label><span><code>top_p</code>{{i18n.t('research.nucleus_sampling','Nucleus sampling')}}</span><input v-model.number="generationDraft.top_p" class="control" type="number" step="0.01" min="0" max="1"></label>
                  <label><span><code>top_k</code>{{i18n.t('research.top_k_sampling','Top-k sampling')}}</span><input v-model.number="generationDraft.top_k" class="control" type="number" min="0"></label>
                  <label><span><code>min_p</code>{{i18n.t('research.minimum_probability','Minimum probability')}}</span><input v-model.number="generationDraft.min_p" class="control" type="number" step="0.01" min="0" max="1"></label>
                  <label><span><code>repeat_penalty</code>{{i18n.t('research.repeat_penalty','Repeat penalty')}}</span><input v-model.number="generationDraft.repeat_penalty" class="control" type="number" step="0.01"></label>
                  <label><span>{{i18n.t('research.seed','Seed')}}</span><input v-model.number="generationDraft.seed" class="control" type="number"></label>
                  <label><span><code>keep_alive</code>{{i18n.t('research.keep_alive','Keep model loaded')}}</span><input v-model="generationDraft.keep_alive" class="control"></label>
                  <label class="wide"><span>{{i18n.t('research.provider_options','Provider options JSON')}}</span><textarea v-model="extraOptions" spellcheck="false"></textarea><small>{{i18n.t('research.provider_options_help','Advanced provider-specific options are merged into this run only.')}}</small></label>
                </div>
              </div>
            </fieldset>
          </section>
        </main>
      </div>
      <footer class="research-settings-studio-footer"><p v-if="settingsError" class="research-settings-error" role="alert">{{settingsError}}</p><span v-else>{{i18n.t('research.settings_apply_note','Changes affect the next Research run; saved provider profiles are not modified.')}}</span><button class="btn" type="button" @click="close">{{i18n.t('ui.cancel','Cancel')}}</button><button class="btn primary" type="button" @click="apply">{{i18n.t('research.apply_settings','Apply to Research')}}</button></footer>
    </div>
  </dialog>
</template>
