<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD
-->

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import UiButton from "../src/components/ui/UiButton.vue";
import UiDialog from "../src/components/ui/UiDialog.vue";
import UiInput from "../src/components/ui/UiInput.vue";
import { type DiscoveredModel, usePublishedSite } from "./siteContext";

const props = defineProps<{
  open: boolean;
  models: DiscoveredModel[];
  current: string;
}>();

const emit = defineEmits<{
  close: [];
  select: [model: string];
}>();

const site = usePublishedSite();
const query = ref("");

watch(
  () => props.open,
  (open) => {
    if (open) query.value = "";
  },
);

const shown = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase();
  return props.models.filter((item) => item.name.toLocaleLowerCase().includes(needle));
});

function select(model: string) {
  emit("select", model);
  emit("close");
}
</script>

<template>
  <UiDialog
    :open="open"
    :title="site.t('site.runtime.models_dialog_title')"
    :close-label="site.t('site.runtime.close')"
    @close="emit('close')"
  >
    <div class="stack">
      <label class="field">
        <span>{{ site.t("site.runtime.filter_models") }}</span>
        <UiInput
          v-model="query"
          class="control"
          type="search"
          autocomplete="off"
          :aria-label="site.t('site.runtime.filter_models')"
        />
      </label>
      <p class="meta" role="status" aria-live="polite">
        {{ site.t("site.runtime.models_match", { count: shown.length }) }}
      </p>
      <ul v-if="shown.length" class="model-list">
        <li v-for="item in shown" :key="item.name">
          <UiButton
            :pressed="item.name === current"
            button-class="model-choice"
            @click="select(item.name)"
          >
            <span class="model-choice-copy">
              <strong>{{ item.name }}</strong>
              <small v-if="item.detail" class="muted">{{ item.detail }}</small>
              <span>{{
                site.t(
                  item.name === current ? "site.runtime.model_in_use" : "site.runtime.use_model",
                )
              }}</span>
            </span>
          </UiButton>
        </li>
      </ul>
      <p v-else>{{ site.t("site.runtime.no_models_match") }}</p>
    </div>
  </UiDialog>
</template>

<style scoped>
.model-list {
  display: grid;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
:deep(.model-choice) {
  width: 100%;
  height: auto;
  justify-content: flex-start;
  text-align: start;
}
.model-choice-copy {
  display: grid;
  gap: 0.15rem;
}
</style>
