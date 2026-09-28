<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { corpusBuildsApi } from "../api/corpus/builds";
import type { CorpusLlmTraceEntry } from "../api/corpus";
import { realtime } from "../realtime";
import type { CorpusGenerationEvent } from "../realtime/protocol";
import { useI18nStore } from "../stores/i18n";

const props = defineProps<{ buildId: string }>();
const i18n = useI18nStore();
const items = ref<CorpusLlmTraceEntry[]>([]);
const loading = ref(false);
const error = ref("");
const open = ref(false);
const drafts = ref<
  Record<string, { text: string; gap: boolean; final: boolean; lastSeq: number }>
>({});
let unsubscribe: (() => void) | null = null;
let liveTimer: number | null = null;

const ordered = computed(() => [...items.value].reverse());

function pretty(value: unknown) {
  return JSON.stringify(value, null, 2);
}

async function load() {
  if (!props.buildId) return;
  loading.value = true;
  error.value = "";
  try {
    const result = await corpusBuildsApi.llmTrace(props.buildId);
    items.value = result.items || [];
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}

async function loadLive() {
  if (!props.buildId || !open.value) return;
  try {
    const result = await corpusBuildsApi.llmLiveOutput(props.buildId);
    const next = { ...drafts.value };
    for (const item of result.items || []) {
      const current = next[item.call_id] || {
        text: "",
        gap: false,
        final: false,
        lastSeq: -1,
      };
      if (item.seq < current.lastSeq) continue;
      next[item.call_id] = {
        text: item.text || "",
        gap: Boolean(item.gap),
        final: false,
        lastSeq: item.seq,
      };
    }
    drafts.value = next;
  } catch {
    // Live drafts are advisory. The persisted trace remains available even if this read fails.
  }
}

function scheduleLiveLoad() {
  if (!open.value) return;
  if (liveTimer !== null) window.clearTimeout(liveTimer);
  liveTimer = window.setTimeout(() => {
    liveTimer = null;
    void loadLive();
  }, 120);
}

function subscribe() {
  unsubscribe?.();
  unsubscribe = null;
  if (!props.buildId) return;
  unsubscribe = realtime.subscribe(`corpus-build:${props.buildId}`, (event) => {
    if (event.type === "corpus.llm_progress") {
      const generation = (event as CorpusGenerationEvent).payload.generation;
      const current = drafts.value[generation.call_id] || {
        text: "",
        gap: false,
        final: false,
        lastSeq: -1,
      };
      if (generation.seq <= current.lastSeq) return;
      drafts.value = {
        ...drafts.value,
        [generation.call_id]: {
          ...current,
          gap: current.gap || generation.gap,
          final: Boolean(generation.final),
          lastSeq: generation.seq,
        },
      };
      if (!items.value.some((item) => item.call_id === generation.call_id)) void load();
      if (generation.final) {
        window.setTimeout(() => void load(), 300);
      } else {
        scheduleLiveLoad();
      }
      return;
    }
    if (open.value && ["llm.completed", "corpus.record_completed"].includes(event.type)) {
      void load();
    }
  });
}

function toggle(event: Event) {
  open.value = (event.currentTarget as HTMLDetailsElement).open;
  if (open.value) {
    subscribe();
    void load();
    void loadLive();
  } else {
    unsubscribe?.();
    unsubscribe = null;
  }
}

watch(
  () => props.buildId,
  () => {
    items.value = [];
    drafts.value = {};
    if (open.value) {
      subscribe();
      void load();
      void loadLive();
    }
  },
);
onBeforeUnmount(() => {
  unsubscribe?.();
  if (liveTimer !== null) window.clearTimeout(liveTimer);
});
</script>

<template>
  <details class="llm-inspector" @toggle="toggle">
    <summary>
      <span>
        <b>{{ i18n.t("pdf_corpus.llm_inspector.title") }}</b>
        <small>{{ i18n.t("pdf_corpus.llm_inspector.help") }}</small>
      </span>
      <span class="trace-count">{{ items.length }}</span>
    </summary>
    <div class="inspector-body">
      <p class="provisional-note">
        {{ i18n.t("pdf_corpus.llm_inspector.provisional_note") }}
      </p>
      <p v-if="loading" role="status">{{ i18n.t("ui.loading") }}</p>
      <p v-else-if="error" role="alert">{{ error }}</p>
      <p v-else-if="!ordered.length">{{ i18n.t("pdf_corpus.llm_inspector.empty") }}</p>
      <article v-for="call in ordered" :key="call.call_id" class="llm-call">
        <header>
          <div>
            <b>{{ call.schema_name || i18n.t("pdf_corpus.llm_inspector.model_call") }}</b>
            <small>
              {{ call.provider || "—" }} · {{ call.model || "—" }} ·
              {{ i18n.tf("pdf_corpus.llm_inspector.attempt", { attempt: call.attempt || 1 }) }}
            </small>
          </div>
          <span>{{ call.status || "—" }}</span>
        </header>
        <div
          v-if="drafts[call.call_id] && !drafts[call.call_id].final"
          class="live-output"
          role="status"
        >
          <b>{{ i18n.t("pdf_corpus.llm_inspector.streaming") }}</b>
          <pre>{{ drafts[call.call_id].text }}</pre>
          <small v-if="drafts[call.call_id].gap">{{
            i18n.t("pdf_corpus.llm_inspector.stream_gap")
          }}</small>
        </div>
        <details>
          <summary>{{ i18n.t("pdf_corpus.llm_inspector.prompt") }}</summary>
          <pre>{{ call.prompt }}</pre>
        </details>
        <details v-if="call.response_schema">
          <summary>{{ i18n.t("pdf_corpus.llm_inspector.response_schema") }}</summary>
          <pre>{{ pretty(call.response_schema) }}</pre>
        </details>
        <details v-if="call.raw_response">
          <summary>{{ i18n.t("pdf_corpus.llm_inspector.raw_output") }}</summary>
          <pre>{{ call.raw_response }}</pre>
        </details>
        <details v-if="call.validated_response">
          <summary>{{ i18n.t("pdf_corpus.llm_inspector.validated_output") }}</summary>
          <pre>{{ pretty(call.validated_response) }}</pre>
        </details>
        <p v-if="call.error" class="call-error" role="alert">{{ call.error }}</p>
      </article>
    </div>
  </details>
</template>

<style scoped>
.llm-inspector {
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  background: var(--surface-raised);
  overflow: clip;
}
.llm-inspector > summary {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3);
  cursor: pointer;
}
.llm-inspector > summary > span:first-child {
  display: grid;
  gap: var(--space-1);
}
.llm-inspector > summary small {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-normal);
}
.trace-count {
  min-width: 1.6rem;
  text-align: center;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
}
.inspector-body {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
.provisional-note {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.llm-call {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--surface-subtle);
}
.llm-call > header {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
  justify-content: space-between;
}
.llm-call > header > div {
  display: grid;
  gap: var(--space-1);
}
.llm-call small {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
}
.llm-call details {
  border-top: 1px solid var(--border-subtle);
  padding-top: var(--space-2);
}
.llm-call summary {
  cursor: pointer;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
pre {
  max-height: 28rem;
  margin: var(--space-2) 0 0;
  overflow: auto;
  padding: var(--space-2);
  border-radius: 8px;
  background: var(--surface-canvas);
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: var(--fs-xs);
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.live-output {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-2);
  border: 1px solid var(--tone-info-border);
  border-radius: 8px;
  background: var(--tone-info-bg);
}
.call-error {
  margin: 0;
  color: var(--tone-danger-fg);
  font-size: var(--fs-sm);
}
</style>
