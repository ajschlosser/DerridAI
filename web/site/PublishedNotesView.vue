<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD
-->

<script setup lang="ts">
import { onMounted, ref } from "vue";
import UiButton from "../src/components/ui/UiButton.vue";
import { usePublishedSite } from "./siteContext";

const site = usePublishedSite();
const items = ref<any[]>([]);
const statusById = ref<Record<string, string>>({});

async function refresh() {
  items.value = site.client.value ? await site.client.value.annotations.list() : [];
}

async function openRecord(recordId: string, annotationId: string) {
  if (!site.client.value) return;
  try {
    const record = await site.client.value.records.get(recordId);
    if (record) site.openRecord(record);
    else {
      statusById.value = {
        ...statusById.value,
        [annotationId]: site.t("site.runtime.record_not_found"),
      };
    }
  } catch (error) {
    statusById.value = {
      ...statusById.value,
      [annotationId]: site.t("site.runtime.record_load_failed", {
        error: error instanceof Error ? error.message : String(error),
      }),
    };
  }
}

async function remove(id: string) {
  if (!site.client.value) return;
  await site.client.value.annotations.remove(id);
  await refresh();
}

onMounted(refresh);
</script>

<template>
  <div
    v-if="!items.length"
    class="panel empty"
    data-tour="notes"
  >
    {{ site.t("site.runtime.no_annotations") }}
  </div>

  <section
    v-else
    class="stack"
    data-tour="notes"
    :aria-label="site.t('site.runtime.annotations')"
  >
    <article v-for="item in items" :key="item.id" class="annotation">
      <strong>{{ item.work || item.record_id }}</strong>
      <div class="meta">{{ site.formatDate(item.created_at) }}</div>
      <blockquote v-if="item.quote">{{ item.quote }}</blockquote>
      <p v-if="item.note">{{ item.note }}</p>
      <div class="chips">
        <span v-for="tag in item.tags || []" :key="tag" class="chip">{{ tag }}</span>
      </div>
      <div class="chips">
        <UiButton
          :label="site.t('site.runtime.view_record')"
          @click="openRecord(item.record_id, item.id)"
        />
        <UiButton
          variant="danger"
          :label="site.t('site.runtime.delete')"
          @click="remove(item.id)"
        />
      </div>
      <span class="status" role="status" aria-live="polite">{{
        statusById[item.id] || ""
      }}</span>
    </article>
  </section>
</template>
