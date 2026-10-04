<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import AppIcon from "../AppIcon.vue";
import PipelineStageList from "../pipelines/PipelineStageList.vue";
import PipelineConfigOverridesEditor from "../pipelines/PipelineConfigOverridesEditor.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import { useI18nStore } from "../../stores/i18n";
import { clonePipelineConfigOverrides, overridesForPipeline } from "../../domain/pipelineOverrides";
import type {
  PipelineAssignment,
  PipelineConfigOverrideSet,
  PipelineDefinition,
  PipelineStrategy,
} from "../../types/pipelines";
import type {
  ResearchConfig,
  ResearchProfile,
  ResearchPromptMetadataPolicy,
} from "../../types/research";

type SettingsSection = "pipeline" | "retrieval" | "evidence" | "generation";
const props = withDefaults(
  defineProps<{
    config: ResearchConfig;
    profiles: ResearchProfile[];
    selectedProfileId: string;
    generation: Record<string, unknown>;
    model: string;
    models: string[];
    metadataFields: string[];
    researcher: boolean;
    pipelineOptions?: PipelineDefinition[];
    pipelineStrategies?: PipelineStrategy[];
    pipelineAssignment?: PipelineAssignment | null;
    pipelineOverrideAllowed?: boolean;
    runPipelineOverrides?: PipelineConfigOverrideSet | null;
  }>(),
  {
    pipelineOptions: () => [],
    pipelineStrategies: () => [],
    pipelineAssignment: null,
    pipelineOverrideAllowed: false,
    runPipelineOverrides: null,
  },
);
const emit = defineEmits<{
  apply: [
    payload: {
      config: Partial<ResearchConfig>;
      generation: Record<string, unknown>;
      model: string;
      runPipelineOverrides: PipelineConfigOverrideSet | null;
    },
  ];
  discover: [];
}>();
const i18n = useI18nStore();
const dialog = ref<HTMLDialogElement | null>(null);
const isOpen = ref(false);
const activeSection = ref<SettingsSection>("retrieval");
const draft = ref<Partial<ResearchConfig>>({});
const generationDraft = ref<Record<string, unknown>>({});
const modelDraft = ref("");
const runOverrideDraft = ref<PipelineConfigOverrideSet | null>(null);
const extraOptions = ref("{}");
const settingsError = ref("");
const selectedProfile = computed(
  () => props.profiles.find((profile) => profile.id === props.selectedProfileId) || null,
);
const assignedPipeline = computed(
  () =>
    props.pipelineOptions.find(
      (pipeline) =>
        pipeline.pipeline_id === props.pipelineAssignment?.pipeline_id &&
        pipeline.version === props.pipelineAssignment?.pipeline_version,
    ) || null,
);
const hasPipelineVisibility = computed(
  () => props.pipelineOptions.length > 0 || props.pipelineAssignment !== null,
);
const settingsTitle = computed(() =>
  hasPipelineVisibility.value
    ? i18n.t("research.pipeline_options_with_chain", "Pipeline, retrieval, evidence & generation")
    : i18n.t("research.pipeline_options"),
);
const selectedPipeline = computed(() => {
  const id = String(draft.value.pipeline_id || "").trim();
  const version = Number(draft.value.pipeline_version || 0);
  if (!id) return assignedPipeline.value;
  return (
    props.pipelineOptions.find(
      (pipeline) => pipeline.pipeline_id === id && pipeline.version === version,
    ) || assignedPipeline.value
  );
});
const settingsOverridesForSelectedPipeline = computed(() =>
  overridesForPipeline(props.config.pipeline_config_overrides, selectedPipeline.value),
);
const pipelineSelection = computed({
  get: () => {
    const id = String(draft.value.pipeline_id || "").trim();
    const version = Number(draft.value.pipeline_version || 0);
    return id && version ? `${id}@${version}` : "";
  },
  set: (value: string) => {
    const raw = String(value || "");
    if (!raw) {
      draft.value.pipeline_id = "";
      draft.value.pipeline_version = null;
      runOverrideDraft.value = null;
      return;
    }
    const split = raw.lastIndexOf("@");
    draft.value.pipeline_id = split > 0 ? raw.slice(0, split) : raw;
    draft.value.pipeline_version = split > 0 ? Number(raw.slice(split + 1)) || null : null;
    runOverrideDraft.value = null;
  },
});
const activeSectionTitle = computed(
  () =>
    ({
      pipeline: i18n.t("research.pipeline_chain", "Pipeline chain"),
      retrieval: i18n.t("research.retrieval"),
      evidence: i18n.t("research.evidence_citations"),
      generation: i18n.t("research.generation"),
    })[activeSection.value],
);

function sync() {
  settingsError.value = "";
  draft.value = {
    pipeline_id: props.config.pipeline_id || "",
    pipeline_version: props.config.pipeline_version || null,
    locales: [...(props.config.locales || [])],
    search_types: [...(props.config.search_types || [])],
    k: props.config.k,
    fetch_k: props.config.fetch_k,
    automatic_sizing: props.config.automatic_sizing,
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
    prompt_metadata: {
      evidence: [...(props.config.prompt_metadata?.evidence || [])],
      context: [...(props.config.prompt_metadata?.context || [])],
      record: [...(props.config.prompt_metadata?.record || [])],
    },
    auto_grade: props.config.auto_grade,
    auto_grade_provider_profile_id: props.config.auto_grade_provider_profile_id,
    use_prior_response_memory: props.config.use_prior_response_memory,
    use_prior_claim_memory: props.config.use_prior_claim_memory,
    memory_profile_id: props.config.memory_profile_id,
  };
  runOverrideDraft.value = clonePipelineConfigOverrides(props.runPipelineOverrides);
  generationDraft.value = { ...props.generation };
  modelDraft.value = props.model || "";
  const raw = props.generation.extra_options;
  extraOptions.value = typeof raw === "string" ? raw : JSON.stringify(raw || {}, null, 2);
}
function open(section: SettingsSection = "pipeline", focusPromptMetadata = false) {
  sync();
  activeSection.value =
    section === "pipeline" && !hasPipelineVisibility.value ? "retrieval" : section;
  isOpen.value = true;
  dialog.value?.showModal();
  void nextTick(() => {
    if (focusPromptMetadata && section === "evidence") {
      const target = dialog.value?.querySelector<HTMLElement>("#research-prompt-metadata");
      target?.scrollIntoView({ block: "start" });
      target?.focus({ preventScroll: true });
      return;
    }
    dialog.value?.querySelector<HTMLElement>(`[data-settings-tab="${section}"]`)?.focus();
  });
}
function close() {
  isOpen.value = false;
  dialog.value?.close();
}
function toggleList(key: "locales" | "search_types", value: string, checked: boolean) {
  const list = new Set((draft.value[key] as string[] | undefined) || []);
  checked ? list.add(value) : list.delete(value);
  draft.value[key] = [...list];
}
function promptMetadataPolicy(): ResearchPromptMetadataPolicy {
  return {
    evidence: [...(draft.value.prompt_metadata?.evidence || [])],
    context: [...(draft.value.prompt_metadata?.context || [])],
    record: [...(draft.value.prompt_metadata?.record || [])],
  };
}
function promptMetadataSelected(scope: keyof ResearchPromptMetadataPolicy, field: string): boolean {
  return promptMetadataPolicy()[scope].includes(field);
}
function togglePromptMetadata(
  scope: keyof ResearchPromptMetadataPolicy,
  field: string,
  checked: boolean,
) {
  const policy = promptMetadataPolicy();
  const values = new Set(policy[scope]);
  checked ? values.add(field) : values.delete(field);
  policy[scope] = [...values];
  draft.value.prompt_metadata = policy;
}

function resetSection(section: SettingsSection) {
  const source = props.config;
  if (section === "pipeline") {
    Object.assign(draft.value, {
      pipeline_id: source.pipeline_id || "",
      pipeline_version: source.pipeline_version || null,
    });
    runOverrideDraft.value = clonePipelineConfigOverrides(props.runPipelineOverrides);
  }
  else if (section === "retrieval")
    Object.assign(draft.value, {
      locales: [...(source.locales || [])],
      search_types: [...(source.search_types || [])],
      k: source.k,
      fetch_k: source.fetch_k,
      automatic_sizing: source.automatic_sizing,
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
      prompt_metadata: {
        evidence: [...(source.prompt_metadata?.evidence || [])],
        context: [...(source.prompt_metadata?.context || [])],
        record: [...(source.prompt_metadata?.record || [])],
      },
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
    runPipelineOverrides: runOverrideDraft.value,
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
          <h2 id="research-settings-title">{{ settingsTitle }}</h2>
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
            v-if="hasPipelineVisibility"
            data-settings-tab="pipeline"
            type="button"
            :class="{ active: activeSection === 'pipeline' }"
            :aria-current="activeSection === 'pipeline' ? 'page' : undefined"
            @click="activeSection = 'pipeline'"
          >
            <AppIcon name="compare" /><span
              ><b>{{ i18n.t("research.pipeline_chain", "Pipeline chain") }}</b
              ><small>{{
                i18n.t(
                  "research.pipeline_chain_nav_help",
                  "Choose and inspect the executable strategy chain.",
                )
              }}</small></span
            >
          </button>
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
            v-if="hasPipelineVisibility"
            v-show="activeSection === 'pipeline'"
            class="research-settings-page"
            aria-labelledby="research-settings-pipeline-title"
          >
            <div class="research-settings-page-head">
              <div>
                <span class="section-label">01</span>
                <h3 id="research-settings-pipeline-title">
                  {{ i18n.t("research.pipeline_chain", "Pipeline chain") }}
                </h3>
                <p>
                  {{
                    i18n.t(
                      "research.pipeline_chain_help",
                      "Every run records the exact immutable pipeline version and the stages that actually executed.",
                    )
                  }}
                </p>
              </div>
              <button class="research-text-action" type="button" @click="resetSection('pipeline')">
                <AppIcon name="refresh" />{{ i18n.t("research.reset_section") }}
              </button>
            </div>

            <fieldset class="research-settings-card pipeline-selection-card">
              <legend>{{ i18n.t("research.pipeline_selection", "Execution chain") }}</legend>
              <p>
                {{
                  i18n.t(
                    "research.pipeline_selection_help",
                    "Use the system assignment or select another authorized executable version for this run.",
                  )
                }}
              </p>
              <label class="pipeline-select-field">
                <span>{{ i18n.t("research.pipeline_chain", "Pipeline chain") }}</span>
                <select
                  v-model="pipelineSelection"
                  class="control"
                  :disabled="!pipelineOverrideAllowed"
                >
                  <option value="">
                    {{
                      assignedPipeline
                        ? `${i18n.t("research.pipeline_system_default", "System default")} · ${assignedPipeline.name} v${assignedPipeline.version}`
                        : i18n.t("research.pipeline_system_default", "System default")
                    }}
                  </option>
                  <option
                    v-for="pipeline in pipelineOptions"
                    :key="`${pipeline.pipeline_id}@${pipeline.version}`"
                    :value="`${pipeline.pipeline_id}@${pipeline.version}`"
                  >
                    {{ pipeline.name }} · v{{ pipeline.version }} · {{ pipeline.status }}
                  </option>
                </select>
                <small v-if="!pipelineOverrideAllowed">
                  {{
                    i18n.t(
                      "research.pipeline_override_locked",
                      "This role follows the system pipeline assignment.",
                    )
                  }}
                </small>
                <small v-else>
                  {{
                    i18n.t(
                      "research.pipeline_override_allowed",
                      "Authorized overrides apply only to this Research configuration; the resolved version is persisted with the run.",
                    )
                  }}
                </small>
              </label>
            </fieldset>

            <div v-if="selectedPipeline" class="pipeline-inspector-card">
              <div class="pipeline-inspector-head">
                <div>
                  <span class="section-label">{{
                    i18n.t("research.pipeline_effective", "Effective chain")
                  }}</span>
                  <h4>{{ selectedPipeline.name }}</h4>
                  <p>
                    <code>{{ selectedPipeline.pipeline_id }}@{{ selectedPipeline.version }}</code>
                    <template v-if="selectedPipeline.notes">
                      · {{ selectedPipeline.notes }}</template
                    >
                  </p>
                </div>
                <span class="pipeline-status-chip">{{ selectedPipeline.status }}</span>
              </div>
              <PipelineStageList :pipeline="selectedPipeline" :strategies="pipelineStrategies" />
            </div>

            <fieldset v-if="selectedPipeline" class="research-settings-card pipeline-run-overrides-card">
              <legend>{{ i18n.t("research.run_pipeline_overrides", "Run overrides") }}</legend>
              <p>
                {{
                  i18n.t(
                    "research.run_pipeline_overrides_help",
                    "These settings apply only to this run. They override both Pipeline Studio configuration and any Settings overrides for this exact pipeline version.",
                  )
                }}
              </p>
              <PipelineConfigOverridesEditor
                v-model="runOverrideDraft"
                :pipeline="selectedPipeline"
                :strategies="pipelineStrategies"
                :inherited-overrides="settingsOverridesForSelectedPipeline"
                layer="run"
              />
            </fieldset>

            <aside v-if="!researcher" class="research-settings-note">
              <AppIcon name="gear" />
              <p>
                {{
                  i18n.t(
                    "research.pipeline_admin_note",
                    "Administrators create, version, validate, and activate chains in System Data → Pipeline Studio.",
                  )
                }}
              </p>
            </aside>
          </section>

          <section
            v-show="activeSection === 'retrieval'"
            class="research-settings-page"
            aria-labelledby="research-settings-retrieval-title"
          >
            <div class="research-settings-page-head">
              <div>
                <span class="section-label">02</span>
                <h3 id="research-settings-retrieval-title">{{ i18n.t("research.retrieval") }}</h3>
                <p>{{
                  i18n.t(
                    "research.retrieval_run_help",
                    "Choose request-level routing and scope for this run. To override a Pipeline Studio stage value, use Run overrides under Pipeline chain.",
                  )
                }}</p>
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
                <legend>{{ i18n.t("research.request_controls", "Run inputs") }}</legend>
                <p>
                  {{
                    i18n.t(
                      "research.request_controls_help",
                      "These values shape this Research request without rewriting stage configuration. Stage-level changes belong under Run overrides in Pipeline chain.",
                    )
                  }}
                </p>
                <label class="research-toggle-setting automatic-sizing-toggle">
                  <input v-model="draft.automatic_sizing" type="checkbox" />
                  <span>
                    <b>{{ i18n.t("research.automatic_sizing", "Automatic sizing") }}</b>
                    <small>{{
                      i18n.t(
                        "research.automatic_sizing_help",
                        "Adapt retrieval depth to Record size while preserving the effective pipeline configuration.",
                      )
                    }}</small>
                  </span>
                </label>
                <div class="research-settings-grid compact">
                  <label>
                    <span>
                      <code>k</code>{{ i18n.t("research.k_label") }}
                      <UiTooltip :text="i18n.t('research.k_help')" />
                    </span>
                    <input
                      v-model.number="draft.k"
                      class="control"
                      type="number"
                      min="1"
                      max="500"
                    />
                  </label>
                  <label class="research-toggle-setting">
                    <input v-model="draft.query_decomposition" type="checkbox" />
                    <span>
                      <b>{{ i18n.t("research.query_decomposition") }}</b>
                      <small>{{
                        i18n.t(
                          "research.query_decomposition_run_help",
                          "Allow the selected pipeline's query-decomposition stage for this run. Its stage configuration is overridden separately.",
                        )
                      }}</small>
                    </span>
                  </label>
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
                <span class="section-label">03</span>
                <h3 id="research-settings-evidence-title">
                  {{ i18n.t("research.evidence_citations") }}
                </h3>
                <p>{{
                  i18n.t(
                    "research.evidence_citations_run_help",
                    "Citation, memory, metadata, and evaluation controls apply to this run. Evidence-packing stage limits are configured under Run overrides.",
                  )
                }}</p>
              </div>
              <button class="research-text-action" type="button" @click="resetSection('evidence')">
                <AppIcon name="refresh" />{{ i18n.t("research.reset_section") }}
              </button>
            </div>
            <div class="research-settings-card-grid">

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
                      ><b
                        >{{ i18n.t("research.use_prior_response_memory") }}
                        <UiTooltip :text="i18n.t('research.use_prior_response_memory_help')" /></b
                      ><small>{{
                        i18n.t("research.use_prior_response_memory_summary")
                      }}</small></span
                    ></label
                  >
                  <label class="research-toggle-setting"
                    ><input v-model="draft.use_prior_claim_memory" type="checkbox" /><span
                      ><b
                        >{{ i18n.t("research.use_prior_claim_memory") }}
                        <UiTooltip :text="i18n.t('research.use_prior_claim_memory_help')" /></b
                      ><small>{{ i18n.t("research.use_prior_claim_memory_summary") }}</small></span
                    ></label
                  >
                </div>
              </fieldset>
              <fieldset
                v-if="isOpen && activeSection === 'evidence'"
                id="research-prompt-metadata"
                class="research-settings-card wide research-prompt-metadata"
                tabindex="-1"
              >
                <legend>
                  {{ i18n.t("research.prompt_metadata", "Prompt metadata") }}
                  <UiTooltip :text="i18n.t('research.prompt_metadata_help')" />
                </legend>
                <p>
                  {{
                    i18n.t(
                      "research.prompt_metadata_summary",
                      "Choose which scholarly metadata fields the model sees; source identity and citation evidence remain separate.",
                    )
                  }}
                </p>
                <div class="research-prompt-metadata-head" aria-hidden="true">
                  <span>{{ i18n.t("research.metadata_field", "Field") }}</span>
                  <span>{{ i18n.t("research.metadata_with_evidence", "Evidence") }}</span>
                  <span>{{ i18n.t("research.metadata_as_context", "Context") }}</span>
                  <span>{{ i18n.t("research.metadata_with_record", "Record") }}</span>
                </div>
                <div class="research-prompt-metadata-rows">
                  <div
                    v-for="field in metadataFields"
                    :key="field"
                    class="research-prompt-metadata-row"
                  >
                    <code>{{ field }}</code>
                    <label
                      ><input
                        type="checkbox"
                        :checked="promptMetadataSelected('evidence', field)"
                        @change="
                          togglePromptMetadata(
                            'evidence',
                            field,
                            ($event.target as HTMLInputElement).checked,
                          )
                        "
                      /><span class="sr-only">{{
                        i18n.t("research.metadata_with_evidence", "Evidence")
                      }}</span></label
                    >
                    <label
                      ><input
                        type="checkbox"
                        :checked="promptMetadataSelected('context', field)"
                        @change="
                          togglePromptMetadata(
                            'context',
                            field,
                            ($event.target as HTMLInputElement).checked,
                          )
                        "
                      /><span class="sr-only">{{
                        i18n.t("research.metadata_as_context", "Context")
                      }}</span></label
                    >
                    <label
                      ><input
                        type="checkbox"
                        :checked="promptMetadataSelected('record', field)"
                        @change="
                          togglePromptMetadata(
                            'record',
                            field,
                            ($event.target as HTMLInputElement).checked,
                          )
                        "
                      /><span class="sr-only">{{
                        i18n.t("research.metadata_with_record", "Record")
                      }}</span></label
                    >
                  </div>
                </div>
                <small>{{
                  i18n.t(
                    "research.prompt_metadata_reproducible",
                    "These selections are stored with the run and restored for reruns.",
                  )
                }}</small>
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
                <span class="section-label">04</span>
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
                    ><span
                      ><code>num_ctx</code>{{ i18n.t("research.context_window") }}
                      <UiTooltip :text="i18n.t('help.glossary.context_window.definition')" /></span
                    ><input
                      v-model.number="generationDraft.num_ctx"
                      class="control"
                      type="number"
                      min="512"
                  /></label>
                  <label
                    ><span
                      ><code>num_predict</code>{{ i18n.t("research.max_output_tokens") }}
                      <UiTooltip :text="i18n.t('providers.max_output_help')" /></span
                    ><input
                      v-model.number="generationDraft.num_predict"
                      class="control"
                      type="number"
                      min="16"
                  /></label>
                  <label
                    ><span
                      >{{ i18n.t("research.thinking") }}
                      <UiTooltip :text="i18n.t('providers.think_help')" /></span
                    ><select v-model="generationDraft.think" class="control">
                      <option value="false">{{ i18n.t("research.off") }}</option>
                      <option value="true">{{ i18n.t("research.on") }}</option>
                      <option value="low">{{ i18n.t("research.thinking_low") }}</option>
                      <option value="medium">{{ i18n.t("research.thinking_medium") }}</option>
                      <option value="high">{{ i18n.t("research.thinking_high") }}</option>
                    </select></label
                  >
                  <label
                    ><span
                      >{{ i18n.t("research.temperature") }}
                      <UiTooltip :text="i18n.t('help.glossary.temperature.definition')" /></span
                    ><input
                      v-model.number="generationDraft.temperature"
                      class="control"
                      type="number"
                      step="0.01"
                      min="0"
                      max="2"
                  /></label>
                  <label
                    ><span
                      ><code>top_p</code>{{ i18n.t("research.nucleus_sampling") }}
                      <UiTooltip :text="i18n.t('help.glossary.top_p.definition')" /></span
                    ><input
                      v-model.number="generationDraft.top_p"
                      class="control"
                      type="number"
                      step="0.01"
                      min="0"
                      max="1"
                  /></label>
                  <label
                    ><span
                      ><code>top_k</code>{{ i18n.t("research.top_k_sampling") }}
                      <UiTooltip :text="i18n.t('providers.top_k_help')" /></span
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
                    ><span
                      >{{ i18n.t("research.seed") }}
                      <UiTooltip :text="i18n.t('help.glossary.seed.definition')" /></span
                    ><input v-model.number="generationDraft.seed" class="control" type="number"
                  /></label>
                  <label
                    ><span
                      ><code>keep_alive</code>{{ i18n.t("research.keep_alive") }}
                      <UiTooltip :text="i18n.t('providers.keep_alive_help')" /></span
                    ><input v-model="generationDraft.keep_alive" class="control"
                  /></label>
                  <label class="wide"
                    ><span
                      >{{ i18n.t("research.provider_options") }}
                      <UiTooltip :text="i18n.t('providers.extra_options_help')" /></span
                    ><textarea v-model="extraOptions" spellcheck="false"></textarea>
                  </label>
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

<style scoped>
.pipeline-selection-card,
.pipeline-inspector-card,
.research-settings-note {
  min-width: 0;
}
.pipeline-select-field {
  display: grid;
  gap: 0.375rem;
  margin-top: 0.75rem;
}
.pipeline-select-field > span {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 800;
}
.pipeline-select-field small {
  color: var(--muted);
  line-height: 1.45;
}
.pipeline-inspector-card {
  display: grid;
  gap: 0.75rem;
  padding: 0.875rem;
  border: 1px solid var(--line);
  border-radius: var(--radius-card, 0.75rem);
  background: var(--card);
}
.pipeline-inspector-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}
.pipeline-inspector-head h4 {
  margin: 0.125rem 0 0;
  color: var(--text-2);
  font-size: 0.9375rem;
}
.pipeline-inspector-head p {
  margin: 0.25rem 0 0;
  color: var(--muted);
  font-size: 0.75rem;
  line-height: 1.45;
}
.pipeline-status-chip {
  flex: 0 0 auto;
  padding: 0.1875rem 0.5rem;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--soft);
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 750;
}
.research-settings-note {
  display: flex;
  gap: 0.625rem;
  align-items: flex-start;
  padding: 0.75rem;
  border: 1px solid var(--line);
  border-radius: var(--radius-control, 0.625rem);
  background: var(--soft);
}
.research-settings-note :deep(svg) {
  flex: 0 0 auto;
  width: 1rem;
  height: 1rem;
  margin-top: 0.125rem;
}
.research-settings-note p {
  margin: 0;
  color: var(--muted);
  font-size: 0.75rem;
  line-height: 1.5;
}
.pipeline-inspector-card :deep(.pipeline-stage-list) {
  margin-top: 0.125rem;
}
.research-prompt-metadata {
  min-width: 0;
}
.research-prompt-metadata-head,
.research-prompt-metadata-row {
  display: grid;
  grid-template-columns: minmax(10rem, 1fr) repeat(3, minmax(4.5rem, 0.28fr));
  gap: 0.5rem;
  align-items: center;
}
.research-prompt-metadata-head {
  padding: 0 0.625rem 0.375rem;
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 800;
}
.research-prompt-metadata-head span:not(:first-child) {
  text-align: center;
}
.research-prompt-metadata-rows {
  max-block-size: 22rem;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: var(--radius-control, 0.625rem);
  background: var(--surface-control, var(--card));
}
.research-prompt-metadata-row {
  min-block-size: 2.75rem;
  padding: 0.375rem 0.625rem;
  border-block-start: 1px solid var(--line);
}
.research-prompt-metadata-row:first-child {
  border-block-start: 0;
}
.research-prompt-metadata-row code {
  overflow-wrap: anywhere;
}
.research-prompt-metadata-row label {
  display: grid;
  place-items: center;
}
.research-prompt-metadata-row input {
  inline-size: 1.125rem;
  block-size: 1.125rem;
}
@media (max-width: 720px) {
  .research-prompt-metadata-head,
  .research-prompt-metadata-row {
    grid-template-columns: minmax(8rem, 1fr) repeat(3, minmax(3.25rem, 0.25fr));
  }
}
</style>
