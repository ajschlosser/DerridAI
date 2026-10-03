<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import {
  useLlmTaskLauncherDialog,
  type LlmLauncherProfile,
  type LlmLauncherRunMode,
} from "../composables/llmTaskLauncherDialog";
import { useI18nStore } from "../stores/i18n";

const { current, close } = useLlmTaskLauncherDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);
const profileId = ref("");
const runMode = ref<LlmLauncherRunMode>("background");
const model = ref("");
const numCtx = ref("");
const think = ref("false");
const numPredict = ref("");
const temperature = ref("");
const topP = ref("");
const seed = ref("");
const extraOptions = ref("{}");
const status = ref("");
const running = ref(false);

const thinkOptions = ["false", "true", "low", "medium", "high"];
const profile = computed<LlmLauncherProfile | null>(
  () => current.value?.profiles.find((item) => item.id === profileId.value) ?? null,
);
const sameModel = computed(() => {
  const request = current.value;
  const active = profile.value;
  if (!request?.generationModel || !active) return false;
  return (
    active.model === request.generationModel &&
    (!request.generationProvider || active.type === request.generationProvider)
  );
});
const baseStatus = computed(() => {
  const active = profile.value;
  if (!active) return "";
  return active.available
    ? i18n.t("jobs.tool.endpoint_ready")
    : active.statusError || i18n.t("providers.not_verified");
});

function loadProfile(active: LlmLauncherProfile | null) {
  if (!active) return;
  model.value = active.autoModel ? "auto" : active.model;
  numCtx.value = String(active.numCtx ?? "");
  think.value = String(active.think ?? "false");
  numPredict.value = String(active.numPredict ?? "");
  temperature.value = String(active.temperature ?? "");
  topP.value = String(active.topP ?? "");
  seed.value = String(active.seed ?? "");
  extraOptions.value = active.extraOptions || "{}";
  status.value = "";
}

// A native modal <dialog> traps focus, makes the page inert and returns focus to the opener on close.
watch(
  current,
  async (request) => {
    if (request) {
      profileId.value = request.profileId;
      runMode.value = request.runMode;
      running.value = false;
      loadProfile(request.profiles.find((item) => item.id === request.profileId) ?? null);
    }
    await nextTick();
    const dialog = dialogRef.value;
    if (!dialog) return;
    if (!request) {
      if (dialog.open) dialog.close();
    } else if (!dialog.open) {
      dialog.showModal();
    }
  },
  { immediate: true },
);

watch(profileId, () => loadProfile(profile.value));

async function warm() {
  const request = current.value;
  if (!request) return;
  status.value = i18n.t("providers.warming");
  status.value = await request.warm(profileId.value);
}

async function run() {
  const request = current.value;
  if (!request || running.value) return;
  running.value = true;
  try {
    const done = await request.run({
      profileId: profileId.value,
      runMode: runMode.value,
      model: model.value,
      numCtx: numCtx.value,
      think: think.value,
      numPredict: numPredict.value,
      temperature: temperature.value,
      topP: topP.value,
      seed: seed.value,
      extraOptions: extraOptions.value,
    });
    if (done && current.value === request) close();
  } finally {
    running.value = false;
  }
}

function manageProviders() {
  const request = current.value;
  close();
  request?.manageProviders();
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="llm-tool-launcher"
    aria-labelledby="llmLauncherTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <template v-if="current && profile">
      <div class="dh">
        <div>
          <h2 id="llmLauncherTitle" class="dialog-title">{{ current.title }}</h2>
          <div class="dialog-subtitle">{{ current.description }}</div>
        </div>
        <button
          class="btn icon-only"
          type="button"
          :aria-label="i18n.t('ui.close')"
          @click="close()"
        >
          ×
        </button>
      </div>
      <div class="db llm-tool-body">
        <section v-if="current.contextText" class="llm-tool-context">
          <span>{{ i18n.t("jobs.tool.question") }}</span>
          <p>{{ current.contextText }}</p>
        </section>
        <div v-if="sameModel" class="info warn" role="alert">
          <b>{{ i18n.t("jobs.tool.same_model_title") }}</b>
          {{ i18n.t("jobs.tool.same_model_help") }}
        </div>
        <div class="llm-tool-grid">
          <div class="field field-wide">
            <label for="toolProvider">{{ i18n.t("jobs.tool.provider_profile") }}</label>
            <select id="toolProvider" v-model="profileId" class="control">
              <option v-for="item in current.profiles" :key="item.id" :value="item.id">
                {{ item.label }} ·
                {{
                  item.type === "ollama"
                    ? i18n.t("jobs.tool.ollama")
                    : i18n.t("jobs.tool.openai_compat")
                }}
              </option>
            </select>
          </div>
          <div class="field">
            <label for="toolRunMode">{{ i18n.t("jobs.tool.run_mode") }}</label>
            <select
              id="toolRunMode"
              v-model="runMode"
              class="control"
              :disabled="current.runModes.length < 2"
            >
              <option v-for="mode in current.runModes" :key="mode" :value="mode">
                {{ i18n.t(`jobs.tool.${mode}`) }}
              </option>
            </select>
          </div>
          <div class="field field-wide">
            <label for="toolModel">{{ i18n.t("providers.model") }}</label>
            <input id="toolModel" v-model="model" class="control" :disabled="profile.autoModel" />
          </div>
          <div class="field">
            <label for="toolConcurrent">{{ i18n.t("jobs.tool.max_concurrent") }}</label>
            <input
              id="toolConcurrent"
              class="control"
              :value="profile.maxConcurrentRequests"
              disabled
            />
          </div>
          <template v-if="profile.type === 'ollama'">
            <div class="field">
              <label for="toolCtx">{{ i18n.t("providers.context") }}</label>
              <input id="toolCtx" v-model="numCtx" class="control" type="number" />
            </div>
            <div class="field">
              <label for="toolThink">{{ i18n.t("providers.think") }}</label>
              <select id="toolThink" v-model="think" class="control">
                <option v-for="value in thinkOptions" :key="value" :value="value">
                  {{
                    i18n.t(
                      `jobs.tool.think_${value === "true" ? "on" : value === "false" ? "off" : value}`,
                    )
                  }}
                </option>
              </select>
            </div>
          </template>
          <div class="field">
            <label for="toolPredict">{{ i18n.t("providers.max_output") }}</label>
            <input id="toolPredict" v-model="numPredict" class="control" type="number" />
          </div>
          <div class="field">
            <label for="toolTemp">{{ i18n.t("providers.temperature") }}</label>
            <input id="toolTemp" v-model="temperature" class="control" type="number" step="0.01" />
          </div>
          <div class="field">
            <label for="toolTopP">{{ i18n.t("providers.top_p") }}</label>
            <input id="toolTopP" v-model="topP" class="control" type="number" step="0.01" />
          </div>
          <div class="field">
            <label for="toolSeed">{{ i18n.t("providers.seed") }}</label>
            <input id="toolSeed" v-model="seed" class="control" type="number" />
          </div>
          <div class="field field-wide">
            <label for="toolExtra">{{ i18n.t("jobs.tool.advanced_json") }}</label>
            <textarea id="toolExtra" v-model="extraOptions" spellcheck="false"></textarea>
          </div>
        </div>
        <div class="tools llm-tool-profile-actions">
          <button class="btn small" type="button" @click="warm()">
            {{ i18n.t("jobs.tool.warm") }}
          </button>
          <button
            v-if="current.canManageProviders"
            class="btn small"
            type="button"
            @click="manageProviders()"
          >
            {{ i18n.t("pdf.manage_providers") }}
          </button>
          <span class="note" role="status">{{ status || baseStatus }}</span>
        </div>
      </div>
      <div class="da">
        <button class="btn" type="button" @click="close()">{{ i18n.t("common.cancel") }}</button>
        <button class="btn primary" type="button" :disabled="running" @click="run()">
          {{
            running
              ? runMode === "background"
                ? i18n.t("jobs.tool.starting")
                : i18n.t("jobs.tool.running")
              : runMode === "background"
                ? i18n.t("jobs.tool.start_background")
                : i18n.t("jobs.tool.run_now")
          }}
        </button>
      </div>
    </template>
  </dialog>
</template>
