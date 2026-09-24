<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { ResearchConfig, ResearchProfile } from "../../types/research";

type SettingsSection = "retrieval" | "evidence" | "generation";
const props = defineProps<{
  config: ResearchConfig;
  profiles: ResearchProfile[];
  selectedProfileId: string;
  generation: Record<string, unknown>;
  model: string;
  models: string[];
  researcher: boolean;
}>();
const emit = defineEmits<{
  apply: [
    payload: {
      config: Partial<ResearchConfig>;
      generation: Record<string, unknown>;
      model: string;
    },
  ];
  discover: [];
}>();
const i18n = useI18nStore();
const dialog = ref<HTMLDialogElement | null>(null);
const activeSection = ref<SettingsSection>("retrieval");
const draft = ref<Partial<ResearchConfig>>({});
const generationDraft = ref<Record<string, unknown>>({});
const modelDraft = ref("");
const extraOptions = ref("{}");
const settingsError = ref("");
const selectedProfile = computed(
  () => props.profiles.find((profile) => profile.id === props.selectedProfileId) || null,
);
const activeSectionTitle = computed(
  () =>
    ({
      retrieval: i18n.t("research.retrieval"),
      evidence: i18n.t("research.evidence_citations"),
      generation: i18n.t("research.generation"),
    })[activeSection.value],
);

function sync() {
  settingsError.value = "";
  draft.value = {
    locales: [...(props.config.locales || [])],
    search_types: [...(props.config.search_types || [])],
    k: props.config.k,
    fetch_k: props.config.fetch_k,
    lambda_mult: props.config.lambda_mult,
    rrf_k: props.config.rrf_k,
    rerank_top_n: props.config.rerank_top_n,
    reranker: props.config.reranker,
    cross_encoder_model: props.config.cross_encoder_model,
    query_decomposition: props.config.query_decomposition,
    query_decomposition_num_predict: props.config.query_decomposition_num_predict,
    evidence_record_char_limit: props.config.evidence_record_char_limit,
    evidence_total_char_limit: props.config.evidence_total_char_limit,
    bind_citations: props.config.bind_citations,
    include_works_cited: props.config.include_works_cited,
    auto_grade: props.config.auto_grade,
    auto_grade_provider_profile_id: props.config.auto_grade_provider_profile_id,
    use_prior_response_memory: props.config.use_prior_response_memory,
    use_prior_claim_memory: props.config.use_prior_claim_memory,
    memory_profile_id: props.config.memory_profile_id,
  };
  generationDraft.value = { ...props.generation };
  modelDraft.value = props.model || "";
  const raw = props.generation.extra_options;
  extraOptions.value = typeof raw === "string" ? raw : JSON.stringify(raw || {}, null, 2);
}
function open() {
  sync();
  activeSection.value = "retrieval";
  dialog.value?.showModal();
  void nextTick(() =>
    dialog.value?.querySelector<HTMLElement>('[data-settings-tab="retrieval"]')?.focus(),
  );
}
function close() {
  dialog.value?.close();
}
function toggleList(key: "locales" | "search_types", value: string, checked: boolean) {
  const list = new Set((draft.value[key] as string[] | undefined) || []);
  checked ? list.add(value) : list.delete(value);
  draft.value[key] = [...list];
}
function resetSection(section: SettingsSection) {
  const source = props.config;
  if (section === "retrieval")
    Object.assign(draft.value, {
      locales: [...(source.locales || [])],
      search_types: [...(source.search_types || [])],
      k: source.k,
      fetch_k: source.fetch_k,
      lambda_mult: source.lambda_mult,
      rrf_k: source.rrf_k,
      rerank_top_n: source.rerank_top_n,
      reranker: source.reranker,
      cross_encoder_model: source.cross_encoder_model,
      query_decomposition: source.query_decomposition,
      query_decomposition_num_predict: source.query_decomposition_num_predict,
    });
  else if (section === "evidence")
    Object.assign(draft.value, {
      evidence_record_char_limit: source.evidence_record_char_limit,
      evidence_total_char_limit: source.evidence_total_char_limit,
      bind_citations: source.bind_citations,
      include_works_cited: source.include_works_cited,
      auto_grade: source.auto_grade,
      auto_grade_provider_profile_id: source.auto_grade_provider_profile_id,
      use_prior_response_memory: source.use_prior_response_memory,
      use_prior_claim_memory: source.use_prior_claim_memory,
      memory_profile_id: source.memory_profile_id,
    });
  else {
    generationDraft.value = { ...props.generation };
    modelDraft.value = props.model || "";
    const raw = props.generation.extra_options;
    extraOptions.value = typeof raw === "string" ? raw : JSON.stringify(raw || {}, null, 2);
  }
}
function apply() {
  try {
    const parsed = JSON.parse(extraOptions.value || "{}");
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") throw new Error();
    generationDraft.value = { ...generationDraft.value, extra_options: parsed };
  } catch {
    settingsError.value = i18n.t("research.invalid_provider_options");
    activeSection.value = "generation";
    return;
  }
  settingsError.value = "";
  emit("apply", {
    config: draft.value,
    generation: generationDraft.value,
    model: modelDraft.value.trim(),
  });
  close();
}
watch(
  () => props.selectedProfileId,
  () => {
    if (dialog.value?.open) sync();
  },
);
defineExpose({ open, close });
</script>

<template>
  <dialog
    ref="dialog"
    class="research-settings-dialog research-settings-studio-dialog"
    aria-labelledby="research-settings-title"
    @cancel.prevent="close"
  >
    <div class="research-settings-studio-shell">
      <header class="research-settings-studio-head">
        <div>
          <span class="section-label">{{ i18n.t("research.expert_settings") }}</span>
          <h2 id="research-settings-title">{{ i18n.t("research.pipeline_options") }}</h2>
          <p>{{ i18n.t("research.expert_help") }}</p>
        </div>
        <div class="research-settings-studio-head-actions">
          <span class="research-settings-profile-pill"
            ><AppIcon name="spark" /><span
              ><small>{{ i18n.t("research.profile") }}</small
              ><b>{{
                selectedProfile?.name || selectedProfile?.id || i18n.t("research.no_profile")
              }}</b></span
            ></span
          >
          <button
            class="btn icon-only"
            type="button"
            :aria-label="i18n.t('ui.close')"
            @click="close"
          >
            ×
          </button>
        </div>
      </header>

      <div class="research-settings-studio-body">
        <nav class="research-settings-nav" :aria-label="i18n.t('research.expert_sections')">
          <button
            data-settings-tab="retrieval"
            type="button"
            :class="{ active: activeSection === 'retrieval' }"
            :aria-current="activeSection === 'retrieval' ? 'page' : undefined"
            @click="activeSection = 'retrieval'"
          >
            <AppIcon name="search" /><span
              ><b>{{ i18n.t("research.retrieval") }}</b
              ><small>{{ i18n.t("research.retrieval_nav_help") }}</small></span
            >
          </button>
          <button
            data-settings-tab="evidence"
            type="button"
            :class="{ active: activeSection === 'evidence' }"
            :aria-current="activeSection === 'evidence' ? 'page' : undefined"
            @click="activeSection = 'evidence'"
          >
            <AppIcon name="record" /><span
              ><b>{{ i18n.t("research.evidence_citations") }}</b
              ><small>{{ i18n.t("research.evidence_nav_help") }}</small></span
            >
          </button>
          <button
            data-settings-tab="generation"
            type="button"
            :class="{ active: activeSection === 'generation' }"
            :aria-current="activeSection === 'generation' ? 'page' : undefined"
            @click="activeSection = 'generation'"
          >
            <AppIcon name="spark" /><span
              ><b>{{ i18n.t("research.generation") }}</b
              ><small>{{ i18n.t("research.generation_nav_help") }}</small></span
            >
          </button>
          <div class="research-settings-nav-note">
            <AppIcon name="history" />
            <p>{{ i18n.t("research.settings_reproducibility_note") }}</p>
          </div>
        </nav>

        <main class="research-settings-panel" :aria-label="activeSectionTitle">
          <section
            v-show="activeSection === 'retrieval'"
            class="research-settings-page"
            aria-labelledby="research-settings-retrieval-title"
          >
            <div class="research-settings-page-head">
              <div>
                <span class="section-label">01</span>
                <h3 id="research-settings-retrieval-title">{{ i18n.t("research.retrieval") }}</h3>
                <p>{{ i18n.t("research.retrieval_expert_help") }}</p>
              </div>
              <button class="research-text-action" type="button" @click="resetSection('retrieval')">
                <AppIcon name="refresh" />{{ i18n.t("research.reset_section") }}
              </button>
            </div>
            <div class="research-settings-card-grid">
              <fieldset class="research-settings-card">
                <legend>{{ i18n.t("research.routing") }}</legend>
                <p>{{ i18n.t("research.routing_help") }}</p>
                <div class="research-settings-choice-row">
                  <span>{{ i18n.t("research.document_languages") }}</span>
                  <div class="research-segmented-checks">
                    <label v-for="code in ['en', 'fr']" :key="code"
                      ><input
                        type="checkbox"
                        :checked="(draft.locales || []).includes(code)"
                        @change="
                          toggleList('locales', code, ($event.target as HTMLInputElement).checked)
                        "
                      /><span>{{
                        code === "en"
                          ? i18n.t("language.english_short")
                          : i18n.t("language.french_short")
                      }}</span></label
                    >
                  </div>
                </div>
                <div class="research-settings-choice-row">
                  <span>{{ i18n.t("research.retrieval_routes") }}</span>
                  <div class="research-segmented-checks">
                    <label
                      v-for="route in [
                        ['similarity', i18n.t('research.similarity')],
                        ['lexical', i18n.t('vector.lexical')],
                        ['mmr', 'MMR'],
                      ]"
                      :key="String(route[0])"
                      ><input
                        type="checkbox"
                        :checked="(draft.search_types || []).includes(String(route[0]))"
                        @change="
                          toggleList(
                            'search_types',
                            String(route[0]),
                            ($event.target as HTMLInputElement).checked,
                          )
                        "
                      /><span>{{ route[1] }}</span></label
                    >
                  </div>
                </div>
              </fieldset>

              <fieldset class="research-settings-card">
                <legend>{{ i18n.t("research.candidate_pool") }}</legend>
                <p>{{ i18n.t("research.candidate_pool_help") }}</p>
                <div class="research-settings-grid compact">
                  <label
                    ><span><code>k</code>{{ i18n.t("research.k_label") }}</span
                    ><input
                      v-model.number="draft.k"
                      class="control"
                      type="number"
                      min="1"
                      max="500"
                    /><small>{{ i18n.t("research.k_help") }}</small></label
                  >
                  <label
                    ><span><code>fetch_k</code>{{ i18n.t("research.fetch_k_label") }}</span
                    ><input
                      v-model.number="draft.fetch_k"
                      class="control"
                      type="number"
                      min="1"
                      max="5000"
                    /><small>{{ i18n.t("research.fetch_k_help") }}</small></label
                  >
                  <label
                    ><span><code>MMR λ</code>{{ i18n.t("research.lambda_label") }}</span
                    ><input
                      v-model.number="draft.lambda_mult"
                      class="control"
                      type="number"
                      step="0.05"
                      min="0"
                      max="1"
                    /><small>{{ i18n.t("research.lambda_help") }}</small></label
                  >
                  <label
                    ><span><code>RRF k</code>{{ i18n.t("research.rrf_label") }}</span
                    ><input
                      v-model.number="draft.rrf_k"
                      class="control"
                      type="number"
                      min="1"
                    /><small>{{ i18n.t("research.rrf_help") }}</small></label
                  >
                </div>
              </fieldset>

              <fieldset class="research-settings-card wide">
                <legend>{{ i18n.t("research.reranking_decomposition") }}</legend>
                <p>{{ i18n.t("research.reranking_decomposition_help") }}</p>
                <div class="research-settings-grid three">
                  <label
                    ><span>{{ i18n.t("research.rerank_top_n") }}</span
                    ><input
                      v-model.number="draft.rerank_top_n"
                      class="control"
                      type="number"
                      min="1"
                      max="500"
                  /></label>
                  <label
                    ><span>{{ i18n.t("research.reranker") }}</span
                    ><select v-model="draft.reranker" class="control">
                      <option value="cross_encoder">{{ i18n.t("research.cross_encoder") }}</option>
                      <option value="lexical">{{ i18n.t("research.lexical_fallback") }}</option>
                      <option value="none">{{ i18n.t("research.none") }}</option>
                    </select></label
                  >
                  <label
                    ><span>{{ i18n.t("research.decomposition_tokens") }}</span
                    ><input
                      v-model.number="draft.query_decomposition_num_predict"
                      class="control"
                      type="number"
                      min="64"
                      max="8192"
                  /></label>
                  <label class="wide"
                    ><span>{{ i18n.t("research.cross_encoder_model") }}</span
                    ><input v-model="draft.cross_encoder_model" class="control"
                  /></label>
                  <label class="research-toggle-setting wide"
                    ><input v-model="draft.query_decomposition" type="checkbox" /><span
                      ><b>{{ i18n.t("research.query_decomposition") }}</b
                      ><small>{{ i18n.t("research.query_decomposition_help") }}</small></span
                    ></label
                  >
                </div>
              </fieldset>
            </div>
          </section>

          <section
            v-show="activeSection === 'evidence'"
            class="research-settings-page"
            aria-labelledby="research-settings-evidence-title"
          >
            <div class="research-settings-page-head">
              <div>
                <span class="section-label">02</span>
                <h3 id="research-settings-evidence-title">
                  {{ i18n.t("research.evidence_citations") }}
                </h3>
                <p>{{ i18n.t("research.evidence_citations_help") }}</p>
              </div>
              <button class="research-text-action" type="button" @click="resetSection('evidence')">
                <AppIcon name="refresh" />{{ i18n.t("research.reset_section") }}
              </button>
            </div>
            <div class="research-settings-card-grid">
              <fieldset class="research-settings-card wide">
                <legend>{{ i18n.t("research.evidence_budget") }}</legend>
                <p>{{ i18n.t("research.evidence_budget_help") }}</p>
                <div class="research-settings-grid two">
                  <label
                    ><span>{{ i18n.t("research.record_char_limit") }}</span
                    ><input
                      v-model.number="draft.evidence_record_char_limit"
                      class="control"
                      type="number"
                      min="500"
                      max="100000"
                    /><small
                      >{{
                        Number(draft.evidence_record_char_limit || 0).toLocaleString(i18n.locale)
                      }}
                      {{ i18n.t("research.characters") }}</small
                    ></label
                  >
                  <label
                    ><span>{{ i18n.t("research.total_char_limit") }}</span
                    ><input
                      v-model.number="draft.evidence_total_char_limit"
                      class="control"
                      type="number"
                      min="5000"
                      max="1000000"
                    /><small
                      >{{
                        Number(draft.evidence_total_char_limit || 0).toLocaleString(i18n.locale)
                      }}
                      {{ i18n.t("research.characters") }}</small
                    ></label
                  >
                </div>
              </fieldset>
              <fieldset class="research-settings-card">
                <legend>{{ i18n.t("research.source_binding") }}</legend>
                <p>{{ i18n.t("research.source_binding_help") }}</p>
                <div class="research-settings-stack">
                  <label class="research-toggle-setting"
                    ><input v-model="draft.bind_citations" type="checkbox" /><span
                      ><b>{{ i18n.t("research.bind_citations") }}</b
                      ><small>{{ i18n.t("research.bind_citations_help") }}</small></span
                    ></label
                  >
                  <label class="research-toggle-setting"
                    ><input v-model="draft.include_works_cited" type="checkbox" /><span
                      ><b>{{ i18n.t("research.include_works_cited") }}</b
                      ><small>{{ i18n.t("research.works_cited_help") }}</small></span
                    ></label
                  >
                  <label class="research-toggle-setting"
                    ><input v-model="draft.use_prior_response_memory" type="checkbox" /><span
                      ><b>{{ i18n.t("research.use_prior_response_memory") }}</b
                      ><small>{{ i18n.t("research.use_prior_response_memory_help") }}</small></span
                    ></label
                  >
                  <label class="research-toggle-setting"
                    ><input v-model="draft.use_prior_claim_memory" type="checkbox" /><span
                      ><b>{{ i18n.t("research.use_prior_claim_memory") }}</b
                      ><small>{{ i18n.t("research.use_prior_claim_memory_help") }}</small></span
                    ></label
                  >
                </div>
              </fieldset>
              <fieldset class="research-settings-card">
                <legend>{{ i18n.t("research.evaluation") }}</legend>
                <p>{{ i18n.t("research.evaluation_help") }}</p>
                <div class="research-settings-stack">
                  <label class="research-toggle-setting"
                    ><input v-model="draft.auto_grade" type="checkbox" /><span
                      ><b>{{ i18n.t("research.auto_grade") }}</b
                      ><small>{{ i18n.t("research.auto_grade_help") }}</small></span
                    ></label
                  >
                  <label v-if="draft.auto_grade"
                    ><span>{{ i18n.t("research.grading_profile") }}</span
                    ><select v-model="draft.auto_grade_provider_profile_id" class="control">
                      <option v-for="profile in profiles" :key="profile.id" :value="profile.id">
                        {{ profile.name || profile.id }} ·
                        {{ profile.model || i18n.t("research.model_auto") }}
                      </option>
                    </select></label
                  >
                </div>
              </fieldset>
            </div>
          </section>

          <section
            v-show="activeSection === 'generation'"
            class="research-settings-page"
            aria-labelledby="research-settings-generation-title"
          >
            <div class="research-settings-page-head">
              <div>
                <span class="section-label">03</span>
                <h3 id="research-settings-generation-title">{{ i18n.t("research.generation") }}</h3>
                <p>
                  {{
                    researcher
                      ? i18n.t("research.researcher_profile_locked")
                      : i18n.t("research.generation_override_help")
                  }}
                </p>
              </div>
              <div class="research-settings-page-actions">
                <button
                  class="research-text-action"
                  type="button"
                  @click="resetSection('generation')"
                >
                  <AppIcon name="refresh" />{{ i18n.t("research.reset_section") }}</button
                ><button v-if="!researcher" class="btn" type="button" @click="emit('discover')">
                  <AppIcon name="search" />{{ i18n.t("research.discover_models") }}
                </button>
              </div>
            </div>
            <fieldset :disabled="researcher" class="research-settings-generation-fieldset">
              <div class="research-generation-model-card">
                <div>
                  <span class="section-label">{{ i18n.t("research.active_profile") }}</span
                  ><b>{{
                    selectedProfile?.name || selectedProfile?.id || i18n.t("research.no_profile")
                  }}</b
                  ><small
                    >{{
                      selectedProfile?.type === "openai"
                        ? i18n.t("providers.openai_compatible")
                        : i18n.t("providers.ollama")
                    }}<template v-if="selectedProfile?.max_concurrent_requests">
                      · {{ selectedProfile.max_concurrent_requests }}
                      {{ i18n.t("research.concurrent_requests") }}</template
                    ></small
                  >
                </div>
                <label
                  ><span>{{ i18n.t("research.model") }}</span
                  ><input
                    v-model="modelDraft"
                    class="control"
                    list="researchSettingsModels"
                    autocomplete="off" /><datalist id="researchSettingsModels">
                    <option v-for="name in models" :key="name" :value="name"></option></datalist
                ></label>
              </div>
              <div class="research-settings-card wide generation-parameters">
                <div class="research-settings-section-head">
                  <div>
                    <b>{{ i18n.t("research.inference_parameters") }}</b
                    ><small>{{ i18n.t("research.inference_parameters_help") }}</small>
                  </div>
                </div>
                <div class="research-settings-grid three">
                  <label
                    ><span><code>num_ctx</code>{{ i18n.t("research.context_window") }}</span
                    ><input
                      v-model.number="generationDraft.num_ctx"
                      class="control"
                      type="number"
                      min="512"
                  /></label>
                  <label
                    ><span><code>num_predict</code>{{ i18n.t("research.max_output_tokens") }}</span
                    ><input
                      v-model.number="generationDraft.num_predict"
                      class="control"
                      type="number"
                      min="16"
                  /></label>
                  <label
                    ><span>{{ i18n.t("research.thinking") }}</span
                    ><select v-model="generationDraft.think" class="control">
                      <option value="false">{{ i18n.t("research.off") }}</option>
                      <option value="true">{{ i18n.t("research.on") }}</option>
                      <option value="low">{{ i18n.t("research.thinking_low") }}</option>
                      <option value="medium">{{ i18n.t("research.thinking_medium") }}</option>
                      <option value="high">{{ i18n.t("research.thinking_high") }}</option>
                    </select></label
                  >
                  <label
                    ><span>{{ i18n.t("research.temperature") }}</span
                    ><input
                      v-model.number="generationDraft.temperature"
                      class="control"
                      type="number"
                      step="0.01"
                      min="0"
                      max="2"
                  /></label>
                  <label
                    ><span><code>top_p</code>{{ i18n.t("research.nucleus_sampling") }}</span
                    ><input
                      v-model.number="generationDraft.top_p"
                      class="control"
                      type="number"
                      step="0.01"
                      min="0"
                      max="1"
                  /></label>
                  <label
                    ><span><code>top_k</code>{{ i18n.t("research.top_k_sampling") }}</span
                    ><input
                      v-model.number="generationDraft.top_k"
                      class="control"
                      type="number"
                      min="0"
                  /></label>
                  <label
                    ><span><code>min_p</code>{{ i18n.t("research.minimum_probability") }}</span
                    ><input
                      v-model.number="generationDraft.min_p"
                      class="control"
                      type="number"
                      step="0.01"
                      min="0"
                      max="1"
                  /></label>
                  <label
                    ><span><code>repeat_penalty</code>{{ i18n.t("research.repeat_penalty") }}</span
                    ><input
                      v-model.number="generationDraft.repeat_penalty"
                      class="control"
                      type="number"
                      step="0.01"
                  /></label>
                  <label
                    ><span>{{ i18n.t("research.seed") }}</span
                    ><input v-model.number="generationDraft.seed" class="control" type="number"
                  /></label>
                  <label
                    ><span><code>keep_alive</code>{{ i18n.t("research.keep_alive") }}</span
                    ><input v-model="generationDraft.keep_alive" class="control"
                  /></label>
                  <label class="wide"
                    ><span>{{ i18n.t("research.provider_options") }}</span
                    ><textarea v-model="extraOptions" spellcheck="false"></textarea
                    ><small>{{ i18n.t("research.provider_options_help") }}</small></label
                  >
                </div>
              </div>
            </fieldset>
          </section>
        </main>
      </div>
      <footer class="research-settings-studio-footer">
        <p v-if="settingsError" class="research-settings-error" role="alert">{{ settingsError }}</p>
        <span v-else>{{ i18n.t("research.settings_apply_note") }}</span
        ><button class="btn" type="button" @click="close">{{ i18n.t("ui.cancel") }}</button
        ><button class="btn primary" type="button" @click="apply">
          {{ i18n.t("research.apply_settings") }}
        </button>
      </footer>
    </div>
  </dialog>
</template>
