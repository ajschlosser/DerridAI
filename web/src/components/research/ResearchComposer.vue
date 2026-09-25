<script setup lang="ts">
import { computed, ref } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type {
  ResearchProfile,
  ResearchPromptMetadataPolicy,
  ResearchStore,
} from "../../types/research";

const props = withDefaults(
  defineProps<{
    prompt: string;
    instructions: string;
    sourceCollection: string;
    providerProfileId: string;
    responseLanguage: string;
    preset: string;
    evidenceCount: number;
    promptMetadata: ResearchPromptMetadataPolicy;
    stores: ResearchStore[];
    profiles: ResearchProfile[];
    history: Array<Record<string, unknown>>;
    busy?: boolean;
    canRun?: boolean;
    canConfigure?: boolean;
    canManageRuns?: boolean;
    disabledReason?: string;
  }>(),
  { busy: false, canRun: true, canConfigure: true, canManageRuns: true, disabledReason: "" },
);
const emit = defineEmits<{
  "update:prompt": [value: string];
  "update:instructions": [value: string];
  "update:sourceCollection": [value: string];
  "update:providerProfileId": [value: string];
  "update:responseLanguage": [value: string];
  "update:preset": [value: string];
  run: [];
  settings: [];
  promptMetadata: [];
  runs: [];
  history: [item: Record<string, unknown>];
}>();
const i18n = useI18nStore();
const historyOpen = ref(false);
const historyQuery = ref("");
const filteredHistory = computed(() => {
  const needle = historyQuery.value.trim().toLocaleLowerCase();
  const rows = props.history.slice(0, 40);
  if (!needle) return rows.slice(0, 8);
  return rows
    .filter((item) =>
      `${item.prompt || ""} ${item.instructions || ""}`.toLocaleLowerCase().includes(needle),
    )
    .slice(0, 12);
});
const selectedProfile = computed(() =>
  props.profiles.find((profile) => profile.id === props.providerProfileId),
);
const selectedStore = computed(() =>
  props.stores.find((store) => store.name === props.sourceCollection),
);
const promptMetadataCounts = computed(() => ({
  evidence: props.promptMetadata?.evidence?.length || 0,
  context: props.promptMetadata?.context?.length || 0,
  record: props.promptMetadata?.record?.length || 0,
}));
function historyLabel(item: Record<string, unknown>) {
  const value = String(item.prompt || item.instructions || i18n.t("research.saved_prompt"))
    .replace(/\s+/g, " ")
    .trim();
  return value.length > 92 ? `${value.slice(0, 89)}…` : value;
}
function pickHistory(item: Record<string, unknown>) {
  emit("history", item);
  historyOpen.value = false;
  historyQuery.value = "";
}
</script>

<template>
  <section class="research-composer-v031 card" aria-labelledby="research-compose-title">
    <header class="research-composer-heading">
      <div>
        <span class="section-label">{{ i18n.t("nav.rag") }}</span>
        <h2 id="research-compose-title">{{ i18n.t("research.ask_title") }}</h2>
        <p>{{ i18n.t("research.ask_help") }}</p>
      </div>
      <div class="research-heading-actions">
        <button v-if="canManageRuns" class="btn" type="button" @click="emit('runs')">
          <AppIcon name="history" />{{ i18n.t("research.runs") }}
        </button>
        <button v-if="canConfigure" class="btn" type="button" @click="emit('settings')">
          <AppIcon name="gear" />{{ i18n.t("research.expert_settings") }}
        </button>
      </div>
    </header>

    <div class="research-question-shell">
      <label class="sr-only" for="researchQuestion">{{ i18n.t("research.question") }}</label>
      <textarea
        id="researchQuestion"
        class="research-question-input"
        :value="prompt"
        :disabled="!canConfigure"
        :placeholder="i18n.t('research.question_placeholder')"
        @input="emit('update:prompt', ($event.target as HTMLTextAreaElement).value)"
      ></textarea>
      <div class="research-question-tools">
        <div class="research-history-popover">
          <button
            class="research-text-action"
            type="button"
            :disabled="!canConfigure"
            :aria-expanded="historyOpen"
            aria-controls="researchHistoryMenu"
            @click="historyOpen = !historyOpen"
          >
            <AppIcon name="history" />{{ i18n.t("research.recent_questions") }}
          </button>
          <div
            v-if="historyOpen"
            id="researchHistoryMenu"
            class="research-history-menu"
            role="dialog"
            :aria-label="i18n.t('research.recent_questions')"
          >
            <label class="sr-only" for="researchHistorySearch">{{
              i18n.t("research.search_history")
            }}</label>
            <input
              id="researchHistorySearch"
              v-model="historyQuery"
              class="control"
              type="search"
              :placeholder="i18n.t('research.search_history')"
              autofocus
            />
            <div class="research-history-list">
              <button
                v-for="(item, index) in filteredHistory"
                :key="String(item.id || index)"
                type="button"
                @click="pickHistory(item)"
              >
                <b>{{ historyLabel(item) }}</b
                ><small>{{ String(item.timestamp || "") }}</small>
              </button>
              <p v-if="!filteredHistory.length" class="note">
                {{ i18n.t("research.no_recent_questions") }}
              </p>
            </div>
          </div>
        </div>
        <span
          >{{ prompt.length.toLocaleString(i18n.locale) }} {{ i18n.t("research.characters") }}</span
        >
      </div>
    </div>

    <details class="research-instructions-disclosure">
      <summary>
        {{ i18n.t("research.instructions")
        }}<span>{{ instructions ? i18n.t("research.added") : i18n.t("research.optional") }}</span>
      </summary>
      <label class="sr-only" for="researchInstructions">{{
        i18n.t("research.instructions")
      }}</label>
      <textarea
        id="researchInstructions"
        :value="instructions"
        :disabled="!canConfigure"
        :placeholder="i18n.t('research.instructions_placeholder')"
        @input="emit('update:instructions', ($event.target as HTMLTextAreaElement).value)"
      ></textarea>
    </details>

    <fieldset class="research-compose-context" :disabled="!canConfigure">
      <legend class="sr-only">{{ i18n.t("research.context") }}</legend>
      <label>
        <span>{{ i18n.t("research.corpus") }}</span>
        <select
          class="control"
          :value="sourceCollection"
          @change="emit('update:sourceCollection', ($event.target as HTMLSelectElement).value)"
        >
          <option v-for="store in stores" :key="store.name" :value="store.name">
            {{ store.name }} · {{ store.count.toLocaleString(i18n.locale) }}
          </option>
          <option v-if="!stores.length" value="">{{ i18n.t("research.no_database") }}</option>
        </select>
        <small v-if="selectedStore"
          >{{ selectedStore.collection_role || "general"
          }}<template v-if="selectedStore.embedding_model">
            · {{ selectedStore.embedding_model }}</template
          ></small
        >
      </label>
      <label>
        <span>{{ i18n.t("research.profile") }}</span>
        <select
          class="control"
          :value="providerProfileId"
          @change="emit('update:providerProfileId', ($event.target as HTMLSelectElement).value)"
        >
          <option v-for="profile in profiles" :key="profile.id" :value="profile.id">
            {{ profile.name || profile.id }}
          </option>
        </select>
        <small>{{ selectedProfile?.model || i18n.t("research.model_auto") }}</small>
      </label>
      <label>
        <span>{{ i18n.t("research.retrieval_profile") }}</span>
        <select
          class="control"
          :value="preset"
          @change="emit('update:preset', ($event.target as HTMLSelectElement).value)"
        >
          <option value="balanced">{{ i18n.t("research.preset_balanced") }}</option>
          <option value="precision">{{ i18n.t("research.preset_precision") }}</option>
          <option value="recall">{{ i18n.t("research.preset_recall") }}</option>
          <option value="evidence" :disabled="evidenceCount === 0">
            {{ i18n.t("research.preset_evidence") }}
          </option>
          <option value="custom">{{ i18n.t("research.preset_custom") }}</option>
        </select>
        <small>{{
          i18n.tf(
            evidenceCount === 1
              ? "research.selected_evidence_count_one"
              : "research.selected_evidence_count_many",
            { count: evidenceCount },
          )
        }}</small>
      </label>
      <div class="research-context-action">
        <span>{{ i18n.t("research.prompt_metadata", "Prompt metadata") }}</span>
        <button
          class="btn research-context-action-button"
          type="button"
          :disabled="!canConfigure"
          @click="emit('promptMetadata')"
        >
          <AppIcon name="record" />{{ i18n.t("research.configure_prompt_metadata") }}
        </button>
        <small>
          {{ i18n.t("research.metadata_with_evidence", "Evidence") }}
          {{ promptMetadataCounts.evidence }} ·
          {{ i18n.t("research.metadata_as_context", "Context") }}
          {{ promptMetadataCounts.context }} ·
          {{ i18n.t("research.metadata_with_record", "Record") }}
          {{ promptMetadataCounts.record }}
        </small>
      </div>
      <label>
        <span>{{ i18n.t("research.answer_language") }}</span>
        <select
          class="control"
          :value="responseLanguage"
          @change="emit('update:responseLanguage', ($event.target as HTMLSelectElement).value)"
        >
          <option value="auto">{{ i18n.t("research.language_auto") }}</option>
          <option value="en">{{ i18n.t("language.english_short") }}</option>
          <option value="fr">{{ i18n.t("language.french_short") }}</option>
        </select>
        <small>{{ i18n.t("research.language_help") }}</small>
      </label>
    </fieldset>

    <footer class="research-compose-footer">
      <div class="research-run-context-summary">
        <span
          ><i></i
          >{{
            evidenceCount
              ? i18n.tf(
                  evidenceCount === 1
                    ? "research.selected_evidence_count_one"
                    : "research.selected_evidence_count_many",
                  { count: evidenceCount },
                )
              : i18n.t("research.retrieval_ready")
          }}</span
        >
        <span>{{
          selectedProfile?.name || selectedProfile?.id || i18n.t("research.no_profile")
        }}</span>
      </div>
      <span class="action-tooltip-wrap" :data-tooltip="!canRun ? disabledReason : ''">
        <button
          class="btn primary research-run-button"
          type="button"
          :disabled="busy || !canRun"
          :aria-disabled="busy || !canRun"
          @click="emit('run')"
        >
          <AppIcon name="spark" />{{ busy ? i18n.t("research.starting") : i18n.t("research.run") }}
        </button>
      </span>
    </footer>
  </section>
</template>

<style scoped>
.research-context-action {
  display: grid;
  gap: 6px;
  align-content: start;
}
.research-context-action > span {
  color: var(--text-primary);
  font-size: 0.8125rem;
  font-weight: 700;
}
.research-context-action-button {
  justify-content: flex-start;
  min-height: var(--control-height);
}
.research-context-action small {
  color: var(--text-tertiary);
  font-size: 0.75rem;
  line-height: 1.35;
}
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
  font-size: 0.8125rem;
  color: var(--muted);
}
</style>
