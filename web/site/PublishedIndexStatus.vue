<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD
-->

<script setup lang="ts">
import { computed, ref } from "vue";
import UiButton from "../src/components/ui/UiButton.vue";
import { usePublishedSite } from "./siteContext";

const props = withDefaults(
  defineProps<{
    prepareLocalModel?: boolean;
    initialBuildLabelKey?: string;
  }>(),
  {
    prepareLocalModel: false,
    initialBuildLabelKey: "",
  },
);

const site = usePublishedSite();
const controller = ref<AbortController | null>(null);
const building = ref(false);
const progressVisible = ref(false);
const progressValue = ref(0);
const progressMax = ref(1);
const liveDetail = ref("");
const outcome = ref("");

const index = computed(() => site.capabilities.value?.localIndex || null);

const storageLabel = computed(() =>
  index.value?.persistent
    ? site.t("site.runtime.index_storage_indexeddb")
    : site.t("site.runtime.index_storage_memory"),
);

const detail = computed(() => {
  if (building.value && liveDetail.value) return liveDetail.value;
  const current = index.value;
  if (!current) return site.t("site.runtime.index_no_provider");
  if (current.usesPublishedVectors) {
    return site.t("site.runtime.index_published", { model: current.model || "" });
  }
  if (current.complete) {
    return site.t("site.runtime.index_ready", {
      count: current.indexed,
      storage: storageLabel.value,
    });
  }
  return site.t(
    site.capabilities.value?.publicationVectors?.available
      ? "site.runtime.index_needed"
      : "site.runtime.index_needed_no_published",
    {
      published: site.sourceEmbeddingModel() || site.t("site.runtime.not_configured"),
      model: current.model || site.localModel.value.model || site.t("site.runtime.not_configured"),
      indexed: current.indexed,
      total: current.total,
      storage: storageLabel.value,
    },
  );
});

const buildLabel = computed(() => {
  const current = index.value;
  if (!current) return site.t("site.runtime.index_build");
  if (current.complete) return site.t("site.runtime.index_rebuild");
  if (current.indexed) return site.t("site.runtime.index_resume");
  return site.t(
    props.initialBuildLabelKey ||
      (props.prepareLocalModel ? "site.runtime.index_build_browser" : "site.runtime.index_build"),
  );
});

async function build() {
  const current = index.value;
  if (!current) return;
  outcome.value = "";
  controller.value = new AbortController();
  building.value = true;
  progressVisible.value = true;
  progressMax.value = Math.max(1, current.total);
  progressValue.value = current.indexed;
  liveDetail.value = site.t("site.runtime.index_preparing", {
    model: current.model || site.localModel.value.model || "",
    total: current.total,
  });

  try {
    await site.buildIndex({
      prepareLocalModel: props.prepareLocalModel,
      signal: controller.value.signal,
      onIndexProgress(indexed, total) {
        progressMax.value = Math.max(1, total);
        progressValue.value = indexed;
        liveDetail.value = site.t("site.runtime.index_progress", { indexed, total });
      },
      onModelProgress(info) {
        if (info?.status === "progress" && info.file) {
          liveDetail.value = site.t("site.runtime.model_download", {
            file: String(info.file).split("/").pop(),
            percent: Math.round(Number(info.progress) || 0),
          });
        }
      },
    });
    outcome.value = site.t("site.runtime.index_done");
  } catch (error) {
    outcome.value =
      error instanceof DOMException && error.name === "AbortError"
        ? site.t("site.runtime.index_cancelled")
        : site.t("site.runtime.index_failed", {
            error: error instanceof Error ? error.message : String(error),
          });
  } finally {
    building.value = false;
    progressVisible.value = false;
    liveDetail.value = "";
    controller.value = null;
  }
}

function cancel() {
  controller.value?.abort();
}

async function clear() {
  if (!window.confirm(site.t("site.runtime.index_clear_confirm"))) return;
  await site.clearIndex();
  outcome.value = "";
}
</script>

<template>
  <div class="provider-summary stack" :data-index="index ? 'ready' : 'none'">
    <strong>{{ site.t("site.runtime.index_heading") }}</strong>
    <div class="meta" role="status" aria-live="polite">{{ detail }}</div>
    <progress
      v-if="progressVisible"
      :value="progressValue"
      :max="progressMax"
      :aria-label="site.t('site.runtime.index_progress_label')"
    ></progress>
    <div v-if="index && !index.usesPublishedVectors" class="chips">
      <UiButton
        :variant="index.complete ? 'default' : 'primary'"
        :label="buildLabel"
        :disabled="building"
        @click="build"
      />
      <UiButton
        v-if="building"
        :label="site.t('site.runtime.index_cancel')"
        @click="cancel"
      />
      <UiButton
        variant="danger"
        :label="site.t('site.runtime.index_clear')"
        :disabled="building || !index.indexed"
        @click="clear"
      />
    </div>
    <div class="status" role="status" aria-live="polite">{{ outcome }}</div>
  </div>
</template>
