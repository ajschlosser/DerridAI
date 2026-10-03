<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD
-->

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import UiButton from "../src/components/ui/UiButton.vue";
import UiCard from "../src/components/ui/UiCard.vue";
import UiInput from "../src/components/ui/UiInput.vue";
import UiSelect from "../src/components/ui/UiSelect.vue";
import PublishedIndexStatus from "./PublishedIndexStatus.vue";
import PublishedModelDialog from "./PublishedModelDialog.vue";
import { type DiscoveredModel, type EndpointProfile, usePublishedSite } from "./siteContext";

const site = usePublishedSite();

const providerStatus = ref("");
const providerStatusTone = ref<"" | "warning" | "error" | "success">("");
const embeddingSelection = ref(site.selectedEmbeddingId.value);
const generationSelection = ref(site.selectedGenerationId.value);

watch(site.selectedEmbeddingId, (value) => {
  embeddingSelection.value = value;
});
watch(site.selectedGenerationId, (value) => {
  generationSelection.value = value;
});

const endpointSummary = computed(() => {
  const embedding = site.endpointById(embeddingSelection.value);
  const generation = site.endpointById(generationSelection.value);
  return [
    embedding
      ? site.t("site.runtime.embedding_uses_endpoint", {
          name: embedding.name,
          model: embedding.model,
        })
      : site.t("site.runtime.embedding_uses_browser"),
    generation
      ? site.t("site.runtime.generation_uses_endpoint", {
          name: generation.name,
          model: generation.model,
        })
      : site.t("site.runtime.provider_generation_none_help"),
  ].join(" ");
});

const localModelName = ref(site.localModel.value.model);
const localDevice = ref(site.localModel.value.device);
const localStatus = ref("");
const localStatusTone = ref<"" | "warning" | "error" | "success">("");
const localProgressVisible = ref(false);
const localProgress = ref(0);
const testingModel = ref(false);

function saveLocalDraft() {
  site.updateLocalModel(localModelName.value, localDevice.value);
}

async function testModel() {
  saveLocalDraft();
  if (!site.localModel.value.model) {
    localStatusTone.value = "warning";
    localStatus.value = site.t("site.runtime.provider_model_required");
    return;
  }
  testingModel.value = true;
  localProgressVisible.value = true;
  localProgress.value = 0;
  localStatusTone.value = "";
  localStatus.value = site.t("site.runtime.model_download_start", {
    model: site.localModel.value.model,
  });
  try {
    const result = await site.testLocalModel((info) => {
      if (info?.status !== "progress") return;
      localProgress.value = Math.round(Number(info.progress) || 0);
      localStatus.value = site.t("site.runtime.model_download", {
        file: String(info.file || site.localModel.value.model).split("/").pop(),
        percent: localProgress.value,
      });
    });
    localStatusTone.value = result.ok ? "success" : "error";
    localStatus.value = result.message;
  } finally {
    localProgressVisible.value = false;
    testingModel.value = false;
  }
}

async function deleteCachedModel() {
  if (!window.confirm(site.t("site.runtime.delete_model_cache_confirm"))) return;
  await site.deleteModelCache();
  localStatusTone.value = "";
  localStatus.value = site.t("site.runtime.model_cache_cleared");
}

async function applyProviderSelection() {
  providerStatusTone.value = "";
  providerStatus.value = site.t("site.runtime.provider_applying");
  try {
    await site.applySelections(embeddingSelection.value, generationSelection.value);
    providerStatus.value = "";
  } catch (error) {
    providerStatusTone.value = "error";
    providerStatus.value = site.t("site.runtime.provider_apply_failed", {
      error: error instanceof Error ? error.message : String(error),
    });
  }
}

async function deleteSelectedEndpoint() {
  const id = generationSelection.value || embeddingSelection.value;
  const endpoint = site.endpointById(id);
  if (!endpoint) {
    providerStatusTone.value = "warning";
    providerStatus.value = site.t("site.runtime.endpoint_select_required");
    return;
  }
  if (!window.confirm(site.t("site.runtime.delete_endpoint_confirm", { name: endpoint.name }))) {
    return;
  }
  await site.removeEndpoint(endpoint.id);
  embeddingSelection.value = site.selectedEmbeddingId.value;
  generationSelection.value = site.selectedGenerationId.value;
  providerStatus.value = "";
  providerStatusTone.value = "";
}

const endpointName = ref("");
const endpointUrl = ref("");
const endpointToken = ref("");
const rememberToken = ref(false);
const endpointModel = ref("");
const useForEmbeddings = ref(false);
const useForAnswers = ref(true);
const endpointStatus = ref("");
const endpointStatusTone = ref<"" | "warning" | "error" | "success">("");
const discoveredModels = ref<DiscoveredModel[]>([]);
const modelDialogOpen = ref(false);

function endpointDraft(): EndpointProfile {
  let base = endpointUrl.value.trim();
  try {
    base = new URL(base).href.replace(/\/$/, "");
  } catch {
    base = base.replace(/\/$/, "");
  }
  return {
    id: "endpoint-draft",
    name: endpointName.value.trim() || "endpoint",
    base_url: base,
    model: endpointModel.value.trim(),
    remember_key: rememberToken.value && Boolean(endpointToken.value),
  };
}

async function discover() {
  endpointStatusTone.value = "";
  endpointStatus.value = site.t("site.runtime.discovering");
  const result = await site.discoverModels(
    endpointDraft(),
    endpointToken.value,
    useForEmbeddings.value && !useForAnswers.value ? "embedding" : "generation",
  );
  if (!result.ok) {
    endpointStatusTone.value = "error";
    endpointStatus.value = result.message;
    return;
  }
  discoveredModels.value = result.models;
  endpointStatusTone.value = result.models.length ? "success" : "warning";
  endpointStatus.value = site.t("site.runtime.models_loaded", {
    count: result.models.length,
  });
  modelDialogOpen.value = true;
}

async function saveEndpoint() {
  endpointStatusTone.value = "";
  endpointStatus.value = site.t("site.runtime.provider_applying");
  try {
    await site.addEndpoint({
      name: endpointName.value,
      baseUrl: endpointUrl.value,
      model: endpointModel.value,
      apiKey: endpointToken.value,
      rememberKey: rememberToken.value,
      useForEmbeddings: useForEmbeddings.value,
      useForAnswers: useForAnswers.value,
    });
    embeddingSelection.value = site.selectedEmbeddingId.value;
    generationSelection.value = site.selectedGenerationId.value;
    endpointName.value = "";
    endpointUrl.value = "";
    endpointToken.value = "";
    rememberToken.value = false;
    endpointModel.value = "";
    useForEmbeddings.value = false;
    useForAnswers.value = true;
    endpointStatus.value = "";
  } catch (error) {
    endpointStatusTone.value = "error";
    endpointStatus.value = error instanceof Error ? error.message : String(error);
  }
}

const activeDeviceText = computed(() =>
  site.activeDevice.value
    ? site.t("site.runtime.local_device_active", {
        device: site.t(
          site.activeDevice.value === "webgpu"
            ? "site.runtime.local_device_webgpu"
            : "site.runtime.local_device_wasm",
        ),
      })
    : site.t("site.runtime.local_model_help"),
);
</script>

<template>
  <section
    class="panel stack provider-panel"
    data-tour="provider"
    aria-labelledby="provider-heading"
  >
    <h2 id="provider-heading">{{ site.t("site.runtime.providers") }}</h2>
    <p class="muted">{{ site.t("site.runtime.providers_intro") }}</p>

    <UiCard class="card stack" heading-id="local-model-heading">
      <h3 id="local-model-heading">{{ site.t("site.runtime.local_model_heading") }}</h3>
      <p class="muted">{{ site.t("site.runtime.local_model_help") }}</p>
      <label class="field">
        <span>{{ site.t("site.runtime.local_model") }}</span>
        <UiInput
          v-model="localModelName"
          class="control"
          list="local-model-options"
          autocomplete="off"
          :aria-label="site.t('site.runtime.local_model')"
          @change="saveLocalDraft"
        />
        <datalist id="local-model-options">
          <option
            v-for="item in site.transformerSuggestions"
            :key="item.id"
            :value="item.id"
            :label="site.t(item.note)"
          ></option>
        </datalist>
      </label>
      <label class="field">
        <span>{{ site.t("site.runtime.local_device") }}</span>
        <UiSelect
          v-model="localDevice"
          class="control"
          :aria-label="site.t('site.runtime.local_device')"
          @change="saveLocalDraft"
        >
          <option value="wasm">{{ site.t("site.runtime.local_device_wasm") }}</option>
          <option value="webgpu">{{ site.t("site.runtime.local_device_webgpu") }}</option>
        </UiSelect>
      </label>
      <div class="meta">{{ activeDeviceText }}</div>
      <progress
        v-if="localProgressVisible"
        :value="localProgress"
        max="100"
        :aria-label="site.t('site.runtime.model_download_label')"
      ></progress>
      <div class="chips">
        <UiButton
          variant="primary"
          :label="site.t('site.runtime.download_model')"
          :disabled="testingModel"
          @click="testModel"
        />
        <UiButton
          variant="danger"
          :label="site.t('site.runtime.delete_model_cache')"
          @click="deleteCachedModel"
        />
      </div>
      <div
        class="status"
        :class="localStatusTone"
        role="status"
        aria-live="polite"
      >
        {{ localStatus }}
      </div>
      <PublishedIndexStatus
        v-if="!site.selectedEmbeddingId.value"
        prepare-local-model
        initial-build-label-key="site.runtime.index_build_browser"
      />
    </UiCard>

    <UiCard class="card stack" heading-id="endpoints-heading">
      <h3 id="endpoints-heading">{{ site.t("site.runtime.endpoints_heading") }}</h3>
      <p class="muted">{{ site.t("site.runtime.endpoints_help") }}</p>
      <label class="field">
        <span>{{ site.t("site.runtime.provider_embedding_heading") }}</span>
        <UiSelect
          v-model="embeddingSelection"
          class="control"
          :aria-label="site.t('site.runtime.provider_embedding_select')"
        >
          <option value="">{{ site.t("site.runtime.local_model_heading") }}</option>
          <option v-for="endpoint in site.endpoints.value" :key="endpoint.id" :value="endpoint.id">
            {{ endpoint.name }} · {{ endpoint.model }}
          </option>
        </UiSelect>
      </label>
      <label class="field">
        <span>{{ site.t("site.runtime.provider_generation_heading") }}</span>
        <UiSelect
          v-model="generationSelection"
          class="control"
          :aria-label="site.t('site.runtime.provider_generation_select')"
        >
          <option value="">{{ site.t("site.runtime.provider_generation_none") }}</option>
          <option v-for="endpoint in site.endpoints.value" :key="endpoint.id" :value="endpoint.id">
            {{ endpoint.name }} · {{ endpoint.model }}
          </option>
        </UiSelect>
      </label>
      <div class="provider-summary meta">{{ endpointSummary }}</div>
      <div class="chips">
        <UiButton
          variant="primary"
          :label="site.t('site.runtime.apply_provider')"
          @click="applyProviderSelection"
        />
        <UiButton
          variant="danger"
          :label="site.t('site.runtime.delete_endpoint')"
          @click="deleteSelectedEndpoint"
        />
      </div>
      <div
        class="status"
        :class="providerStatusTone"
        role="status"
        aria-live="polite"
      >
        {{ providerStatus }}
      </div>
      <PublishedIndexStatus v-if="site.selectedEmbeddingId.value" />
    </UiCard>

    <form
      class="provider-form"
      aria-labelledby="provider-add-heading"
      @submit.prevent="saveEndpoint"
    >
      <h3 id="provider-add-heading">{{ site.t("site.runtime.add_endpoint") }}</h3>
      <p class="muted">{{ site.t("site.runtime.provider_local_help") }}</p>
      <label class="field">
        <span>{{ site.t("site.runtime.endpoint_name") }}</span>
        <UiInput
          v-model="endpointName"
          class="control"
          required
          autocomplete="off"
          :placeholder="site.t('site.runtime.endpoint_name_placeholder')"
        />
      </label>
      <label class="field">
        <span>{{ site.t("site.runtime.provider_url") }}</span>
        <UiInput
          v-model="endpointUrl"
          class="control"
          required
          type="text"
          inputmode="url"
          autocomplete="url"
          :placeholder="site.t('site.runtime.provider_url_placeholder')"
        />
      </label>
      <label class="field">
        <span>{{ site.t("site.runtime.api_token") }}</span>
        <UiInput
          v-model="endpointToken"
          class="control"
          type="password"
          autocomplete="off"
          :placeholder="site.t('site.runtime.api_token_optional')"
        />
        <small class="muted">{{ site.t("site.runtime.api_token_help") }}</small>
      </label>
      <label class="toggle">
        <input v-model="rememberToken" type="checkbox" />
        <span>{{ site.t("site.runtime.store_token") }}</span>
      </label>
      <label class="field">
        <span>{{ site.t("site.runtime.provider_model") }}</span>
        <UiInput
          v-model="endpointModel"
          class="control"
          required
          autocomplete="off"
          list="endpoint-model-options"
          :placeholder="site.t('site.runtime.provider_model_placeholder')"
        />
        <datalist id="endpoint-model-options">
          <option v-for="item in discoveredModels" :key="item.name" :value="item.name"></option>
        </datalist>
      </label>
      <div class="chips">
        <UiButton :label="site.t('site.runtime.discover_models')" @click="discover" />
      </div>
      <label class="toggle">
        <input v-model="useForEmbeddings" type="checkbox" />
        <span>{{ site.t("site.runtime.use_for_embeddings") }}</span>
      </label>
      <label class="toggle">
        <input v-model="useForAnswers" type="checkbox" />
        <span>{{ site.t("site.runtime.use_for_answers") }}</span>
      </label>
      <div class="chips">
        <UiButton
          variant="primary"
          type="submit"
          :label="site.t('site.runtime.save_provider')"
        />
      </div>
      <div
        class="status"
        :class="endpointStatusTone"
        role="status"
        aria-live="polite"
      >
        {{ endpointStatus }}
      </div>
    </form>

    <PublishedModelDialog
      :open="modelDialogOpen"
      :models="discoveredModels"
      :current="endpointModel"
      @close="modelDialogOpen = false"
      @select="endpointModel = $event"
    />
  </section>
</template>
