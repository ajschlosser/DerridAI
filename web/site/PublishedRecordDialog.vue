<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD
-->

<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import UiButton from "../src/components/ui/UiButton.vue";
import UiDialog from "../src/components/ui/UiDialog.vue";
import UiInput from "../src/components/ui/UiInput.vue";
import UiTextarea from "../src/components/ui/UiTextarea.vue";
import { usePublishedSite } from "./siteContext";
import { highlightSegments } from "./textHighlight";

const site = usePublishedSite();
const quote = ref("");
const note = ref("");
const tags = ref("");
const saved = ref("");

const state = computed(() => site.recordDialog.value);
const record = computed(() => state.value?.record || null);
const searchedQuery = computed(() => state.value?.searchedQuery || "");

const textSegments = computed(() =>
  highlightSegments(
    String(record.value?.text || ""),
    searchedQuery.value,
    site.locale.value,
  ),
);

const metadata = computed(() => {
  if (!record.value) return [];
  return Object.entries(record.value)
    .sort(([left], [right]) => left.localeCompare(right))
    .filter(
      ([key, value]) =>
        !["text", "field_assertions", "source_spans"].includes(key) &&
        value != null &&
        value !== "" &&
        (typeof value !== "object" || Array.isArray(value)),
    )
    .map(([key, value]) => ({
      key,
      label: key.replaceAll("_", " "),
      value: Array.isArray(value)
        ? value
            .map((item) => (typeof item === "object" ? JSON.stringify(item) : String(item)))
            .join(", ")
        : String(value),
    }));
});

watch(
  () => state.value?.record.record_id,
  async () => {
    quote.value = "";
    note.value = "";
    tags.value = "";
    saved.value = "";
    if (state.value) {
      await nextTick();
      document.querySelector(".ui-dialog .record-text mark")?.scrollIntoView({ block: "center" });
    }
  },
);

async function saveAnnotation() {
  if (!record.value || !site.client.value) return;
  if (!quote.value.trim() && !note.value.trim() && !tags.value.trim()) return;
  await site.client.value.annotations.add({
    recordId: String(record.value.record_id),
    recordRevision:
      record.value.record_revision == null ? undefined : String(record.value.record_revision),
    work: record.value.work == null ? undefined : String(record.value.work),
    quote: quote.value,
    note: note.value,
    tags: tags.value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
  });
  quote.value = "";
  note.value = "";
  tags.value = "";
  saved.value = site.t("site.runtime.annotation_saved");
}
</script>

<template>
  <UiDialog
    :open="Boolean(state)"
    :title="String(record?.work || record?.record_id || '')"
    :close-label="site.t('site.runtime.close')"
    size="large"
    @close="site.closeRecord"
  >
    <template v-if="record">
      <div class="record-dialog-content">
        <div class="meta">{{ site.client.value?.citations.format(record).plain }}</div>
        <div class="record-text" tabindex="0">
          <template v-for="(segment, index) in textSegments" :key="index">
            <mark v-if="segment.highlighted">{{ segment.text }}</mark>
            <template v-else>{{ segment.text }}</template>
          </template>
        </div>

        <dl class="metadata">
          <template v-for="item in metadata" :key="item.key">
            <dt>{{ item.label }}</dt>
            <dd>{{ item.value }}</dd>
          </template>
        </dl>

        <h3>{{ site.t("site.runtime.add_annotation") }}</h3>
        <UiTextarea
          v-model="quote"
          class="control"
          :placeholder="site.t('site.runtime.quote_placeholder')"
          :aria-label="site.t('site.runtime.quotation')"
        />
        <UiTextarea
          v-model="note"
          class="control"
          :placeholder="site.t('site.runtime.note_placeholder')"
          :aria-label="site.t('site.runtime.note')"
        />
        <UiInput
          v-model="tags"
          class="control"
          :placeholder="site.t('site.runtime.tags_placeholder')"
          :aria-label="site.t('site.runtime.tags')"
        />
        <div class="chips">
          <UiButton
            variant="primary"
            :label="site.t('site.runtime.save_annotation')"
            @click="saveAnnotation"
          />
        </div>
        <span class="status success" role="status" aria-live="polite">{{ saved }}</span>
      </div>
    </template>
  </UiDialog>
</template>

<style scoped>
.record-dialog-content {
  display: grid;
  gap: 1rem;
}
.record-dialog-content h3 {
  margin-block-end: 0;
}
</style>
