<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import {
  corpusCaptureApi,
  type AuthorCandidate,
  type CaptureCandidate,
  type CorpusCapture,
  type SourceProviderId,
  type SourceProviderInfo,
} from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import { useCapturePolling } from "../../composables/useCapturePolling";
import {
  acquirableCount,
  includesFromOptions,
  optionsFromIncludes,
  stepForCapture,
  type CaptureIncludes,
  type CaptureStep,
} from "../../domain/captureReview";
import UiDialog from "../ui/UiDialog.vue";
import AppIcon from "../AppIcon.vue";
import CaptureAuthorResolver from "./CaptureAuthorResolver.vue";
import CaptureOptionsForm from "./CaptureOptionsForm.vue";
import CaptureProgress from "./CaptureProgress.vue";
import CaptureReview from "./CaptureReview.vue";
import CaptureCompletion from "./CaptureCompletion.vue";

/**
 * Capture an author: resolve the person, choose libraries/roles/languages, watch discovery, review
 * the candidates, and acquire the chosen ones as sources. Closing the dialog never stops the
 * background job; reopening a capture restores the step its durable status belongs to.
 */
const props = withDefaults(defineProps<{ open?: boolean; captureId?: string }>(), {
  open: true,
  captureId: "",
});
const emit = defineEmits<{
  close: [];
  viewSources: [captureId: string];
  useInBuilder: [sourceIds: string[]];
  changed: [capture: CorpusCapture];
}>();
const i18n = useI18nStore();

const step = ref<CaptureStep>("author");
const author = ref<AuthorCandidate | null>(null);
const providers = ref<SourceProviderId[]>(["gutenberg", "wikisource"]);
const includes = ref<CaptureIncludes>({
  authored: true,
  translations: true,
  translator: false,
  editor: false,
  other: false,
});
const languages = ref<string[] | null>(null);
const providerInfo = ref<SourceProviderInfo[]>([]);
const candidates = ref<CaptureCandidate[]>([]);
const busy = ref(false);
const error = ref("");

const polling = useCapturePolling({
  onUpdate: (next) => {
    emit("changed", next);
    // Follow a running job's phase; an idle capture stays on the step the user chose.
    if (next.active_job) step.value = stepForCapture(next);
  },
  onSettled: (next) => {
    step.value = stepForCapture(next);
    void loadCandidates();
  },
});
const capture = polling.capture;

const optionsValid = computed(
  () =>
    providers.value.length > 0 &&
    (includes.value.authored ||
      includes.value.translations ||
      includes.value.translator ||
      includes.value.editor ||
      includes.value.other) &&
    (includes.value.translations
      ? languages.value === null || Boolean(languages.value.length)
      : Boolean(languages.value?.length === 1)),
);
const toAcquire = computed(() => acquirableCount(candidates.value));
const running = computed(() => Boolean(capture.value?.active_job));
const title = computed(() =>
  capture.value
    ? i18n.tf("capture.dialog.title_named", { author: capture.value.author.canonical_name })
    : i18n.t("capture.dialog.title"),
);
const STEPS: CaptureStep[] = ["author", "options", "discovering", "review", "acquiring", "done"];
const stepIndex = computed(() => STEPS.indexOf(step.value));

function fail(cause: unknown) {
  error.value = cause instanceof Error ? cause.message : String(cause);
}

async function loadCandidates() {
  const id = capture.value?.capture_id;
  if (!id) return;
  const rows: CaptureCandidate[] = [];
  try {
    for (let offset = 0; ; offset += 1000) {
      const page = await corpusCaptureApi.candidates(id, { offset, limit: 1000 });
      rows.push(...page.items);
      if (rows.length >= page.total || !page.items.length) break;
    }
    candidates.value = rows;
  } catch (cause) {
    fail(cause);
  }
}

async function openCapture(id: string) {
  error.value = "";
  const loaded = await polling.load(id);
  if (!loaded) {
    error.value ||= polling.error.value;
    return;
  }
  const options = loaded.options;
  providers.value = [...options.providers];
  includes.value = includesFromOptions(options);
  languages.value = options.languages ? [...options.languages] : null;
  step.value = stepForCapture(loaded);
  if (["review", "done"].includes(step.value) || loaded.discovery_completed_at)
    await loadCandidates();
}

async function start() {
  if (!author.value || !optionsValid.value) return;
  busy.value = true;
  error.value = "";
  try {
    const created = await corpusCaptureApi.createCapture(
      author.value.wikidata_qid,
      optionsFromIncludes(providers.value, includes.value, languages.value),
      (i18n.locale || "en").split("-")[0].toLowerCase(),
    );
    step.value = "discovering";
    polling.accept(created);
    if (!created.active_job) step.value = stepForCapture(created);
  } catch (cause) {
    fail(cause);
  } finally {
    busy.value = false;
  }
}

async function run(action: "discover" | "acquire" | "retry" | "refresh" | "cancel") {
  const id = capture.value?.capture_id;
  if (!id) return;
  busy.value = true;
  error.value = "";
  try {
    const next = await corpusCaptureApi[action](id);
    if (action === "acquire" || action === "retry") step.value = "acquiring";
    if (action === "discover" || action === "refresh") step.value = "discovering";
    polling.accept(next);
    if (!next.active_job) {
      step.value = stepForCapture(next);
      await loadCandidates();
    }
  } catch (cause) {
    fail(cause);
  } finally {
    busy.value = false;
  }
}

async function select(ids: string[] | null, selected: boolean) {
  const id = capture.value?.capture_id;
  if (!id) return;
  busy.value = true;
  try {
    const next = await corpusCaptureApi.setSelection(id, ids, selected);
    const wanted = ids ? new Set(ids) : null;
    candidates.value = candidates.value.map((item) =>
      !wanted || wanted.has(item.candidate_id)
        ? {
            ...item,
            selection_status: selected ? "selected" : "excluded",
            selection_reason: "user",
          }
        : item,
    );
    polling.accept(next);
  } catch (cause) {
    fail(cause);
  } finally {
    busy.value = false;
  }
}

async function loadProviders() {
  try {
    providerInfo.value = (await corpusCaptureApi.sourceProviders()).items;
  } catch {
    providerInfo.value = [];
  }
}

function reset() {
  polling.reset();
  step.value = "author";
  author.value = null;
  candidates.value = [];
  error.value = "";
}

watch(
  () => [props.open, props.captureId] as const,
  ([open, id], previous) => {
    if (!open) return;
    if (id && id !== capture.value?.capture_id) void openCapture(id);
    else if (!id && previous?.[1]) reset();
  },
);
onMounted(() => {
  void loadProviders();
  if (props.open && props.captureId) void openCapture(props.captureId);
});
</script>

<template>
  <UiDialog
    :open="open"
    :title="title"
    :description="i18n.t('capture.dialog.description')"
    :close-label="i18n.t('common.close')"
    size="xlarge"
    @close="emit('close')"
  >
    <ol class="capture-steps" :aria-label="i18n.t('capture.dialog.steps')">
      <li
        v-for="(item, index) in STEPS"
        :key="item"
        :aria-current="item === step ? 'step' : undefined"
        :data-done="index < stepIndex"
      >
        {{ i18n.t(`capture.step.${item}`) }}
      </li>
    </ol>

    <p v-if="error" class="capture-error" role="alert">
      <AppIcon name="warning" /><span>{{ error }}</span>
    </p>

    <CaptureAuthorResolver v-if="step === 'author'" v-model="author" />
    <CaptureOptionsForm
      v-else-if="step === 'options'"
      v-model:providers="providers"
      v-model:includes="includes"
      v-model:languages="languages"
      :author="author"
      :provider-info="providerInfo"
    />
    <template v-else-if="capture && (step === 'discovering' || step === 'acquiring')">
      <CaptureProgress :capture="capture" :mode="step" />
      <p
        v-if="!running && ['interrupted', 'cancelled', 'failed'].includes(capture.status)"
        role="status"
      >
        {{ i18n.t(`capture.dialog.stopped_${capture.status}`) }}
      </p>
    </template>
    <template v-else-if="capture && step === 'review'">
      <p
        v-if="capture.status === 'interrupted' || capture.status === 'cancelled'"
        class="capture-notice"
        role="status"
      >
        {{ i18n.t(`capture.dialog.stopped_${capture.status}`) }}
      </p>
      <CaptureReview :capture="capture" :candidates="candidates" :busy="busy" @select="select" />
    </template>
    <CaptureCompletion
      v-else-if="capture && step === 'done'"
      :capture="capture"
      :candidates="candidates"
      :busy="busy || running"
      @view-sources="emit('viewSources', capture.capture_id)"
      @retry="run('retry')"
      @use-in-builder="emit('useInBuilder', $event)"
    />
    <p v-else class="capture-loading" role="status">{{ i18n.t("sources.loading") }}</p>

    <template #footer>
      <div class="capture-footer">
        <template v-if="step === 'author'">
          <button type="button" class="btn" @click="emit('close')">
            {{ i18n.t("common.cancel") }}
          </button>
          <button
            type="button"
            class="btn primary"
            data-action="next"
            :disabled="!author"
            @click="step = 'options'"
          >
            {{ i18n.t("capture.dialog.choose_person") }}
          </button>
        </template>
        <template v-else-if="step === 'options'">
          <button type="button" class="btn" @click="step = 'author'">
            {{ i18n.t("ui.back") }}
          </button>
          <button
            type="button"
            class="btn primary"
            data-action="discover"
            :disabled="!optionsValid || busy"
            @click="start"
          >
            {{ i18n.t("capture.dialog.discover") }}
          </button>
        </template>
        <template v-else-if="step === 'discovering' || step === 'acquiring'">
          <button
            v-if="running"
            type="button"
            class="btn"
            data-action="cancel"
            :disabled="busy || capture?.active_job?.status === 'cancelling'"
            @click="run('cancel')"
          >
            {{ i18n.t("capture.dialog.cancel_job") }}
          </button>
          <button
            v-else-if="step === 'discovering'"
            type="button"
            class="btn"
            data-action="rediscover"
            :disabled="busy"
            @click="run('discover')"
          >
            {{ i18n.t("capture.dialog.discover_again") }}
          </button>
          <button type="button" class="btn primary" @click="emit('close')">
            {{ i18n.t("capture.dialog.close_background") }}
          </button>
        </template>
        <template v-else-if="step === 'review'">
          <button
            type="button"
            class="btn"
            data-action="refresh"
            :disabled="busy"
            @click="run('refresh')"
          >
            {{ i18n.t("capture.dialog.refresh") }}
          </button>
          <button
            type="button"
            class="btn primary"
            data-action="acquire"
            :disabled="!toAcquire || busy"
            @click="run('acquire')"
          >
            {{ i18n.tf("capture.dialog.acquire", { count: toAcquire }) }}
          </button>
        </template>
        <template v-else-if="step === 'done'">
          <button type="button" class="btn" @click="step = 'review'">
            {{ i18n.t("capture.dialog.back_to_review") }}
          </button>
          <button type="button" class="btn primary" @click="emit('close')">
            {{ i18n.t("common.close") }}
          </button>
        </template>
      </div>
    </template>
  </UiDialog>
</template>

<style scoped>
.capture-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  margin: 0 0 16px;
  padding: 0;
  list-style: none;
  counter-reset: capture-step;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.capture-steps li {
  counter-increment: capture-step;
}
.capture-steps li::before {
  content: counter(capture-step) ". ";
}
.capture-steps li[aria-current="step"] {
  color: var(--text-primary);
  font-weight: var(--fw-bold);
  text-decoration: underline;
  text-underline-offset: 4px;
}
.capture-steps li[data-done="true"] {
  color: var(--text-primary);
}
.capture-error,
.capture-notice {
  display: flex;
  gap: 6px;
  margin: 0 0 12px;
  padding: 8px 10px;
  border-radius: var(--radius-control);
  font-size: var(--fs-sm);
}
.capture-error {
  border: 1px solid var(--tone-danger-border);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.capture-notice {
  border: 1px solid var(--tone-warn-border);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.capture-loading {
  color: var(--text-secondary);
}
.capture-footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  width: 100%;
}
</style>
