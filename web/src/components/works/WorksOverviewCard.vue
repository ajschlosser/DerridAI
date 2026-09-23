<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";
import MixedValueInspect from "./MixedValueInspect.vue";
import WorksInsightCard from "./WorksInsightCard.vue";
import type { WorksItem } from "../../types/works";
import { statusTone } from "../../domain/status";
import UiStatusBadge from "../ui/UiStatusBadge.vue";

const props = withDefaults(
  defineProps<{
    work: WorksItem;
    mode?: "admin" | "researcher";
    citationLabel?: string;
  }>(),
  { mode: "admin", citationLabel: "" },
);
const emit = defineEmits<{
  search: [];
  edit: [];
  populate: [];
  annotations: [];
  browse: [];
  inspect: [field: string];
  insight: [field: string, value: string];
}>();
const i18n = useI18nStore();
</script>
<template>
  <section class="card work-overview-card" aria-labelledby="selected-work-title">
    <div class="work-overview-cover">
      <img
        v-if="props.work.cover"
        :src="props.work.cover"
        :alt="i18n.tf('works.cover_alt', 'Cover of {work}', { work: props.work.work })"
        :loading="props.mode === 'admin' ? 'lazy' : undefined"
      />
      <div v-else-if="props.mode === 'admin'" class="work-cover-placeholder">
        <AppIcon name="books" aria-hidden="true" />
      </div>
      <AppIcon v-else name="books" aria-hidden="true" />
    </div>
    <div class="work-overview-content">
      <div class="work-overview-heading">
        <div>
          <span class="section-label">{{ i18n.t("works.overview", "Work overview") }}</span>
          <h1 id="selected-work-title">{{ props.work.work }}</h1>
          <p v-if="props.mode === 'admin'">
            {{ props.work.count.toLocaleString(i18n.locale) }}
            {{ i18n.t("dynamic.records", "records") }} ·
            {{ props.work.files.length.toLocaleString(i18n.locale) }}
            {{ i18n.t("works.source_files", "source files") }}
          </p>
          <p v-else>
            {{ props.work.count.toLocaleString(i18n.locale) }}
            {{ i18n.t("dynamic.records", "records") }}
          </p>
        </div>
        <UiStatusBadge
          v-if="props.mode === 'admin'"
          :label="props.work.status.label"
          :tone="statusTone(props.work.status.kind)"
          :data-work-status="props.work.work"
        />
      </div>
      <div class="work-overview-metadata">
        <div v-for="item in props.work.metadata" :key="item.field">
          <span>{{ item.field_label }}</span>
          <MixedValueInspect
            v-if="item.mixed"
            :field="item.field"
            :field-label="item.field_label"
            :count="item.unique_count"
            @inspect="emit('inspect', $event)"
          />
          <b v-else>{{ item.value }}</b>
        </div>
      </div>
      <div v-if="props.mode === 'admin' || props.work.citation" class="work-overview-citation">
        <span>{{ props.citationLabel }}</span>
        <p>{{ props.work.citation }}</p>
      </div>
      <section
        v-if="props.mode === 'admin'"
        class="work-insights-panel"
        :aria-label="i18n.t('works.work_insights', 'Work insights')"
      >
        <div class="work-insights-heading">
          <div>
            <span class="section-label">{{ i18n.t("works.work_insights", "Work insights") }}</span>
            <h2>{{ i18n.t("works.indexed_patterns", "Metadata patterns in this work") }}</h2>
          </div>
          <p>
            {{
              i18n.t(
                "works.work_insights_help",
                "Counts come from populated metadata on the loaded records, not from the vector index. Empty cards mean this work has no usable values for that field yet.",
              )
            }}
          </p>
        </div>
        <div class="work-insights-grid">
          <WorksInsightCard
            v-for="insight in props.work.insights"
            :key="insight.id"
            :insight="insight"
            @search="(field, value) => emit('insight', field, value)"
          />
        </div>
      </section>
      <div class="work-overview-actions">
        <template v-if="props.mode === 'admin'">
          <button id="overviewSearchWork" type="button" class="btn primary" @click="emit('search')">
            <AppIcon name="search" aria-hidden="true" />{{
              i18n.t("works.search_records", "Search records")
            }}
          </button>
          <button id="overviewEditWork" type="button" class="btn" @click="emit('edit')">
            <AppIcon name="edit" aria-hidden="true" />{{
              i18n.t("works.edit_metadata", "Edit work metadata")
            }}
          </button>
          <button
            id="overviewPopulateWork"
            type="button"
            class="btn soft"
            @click="emit('populate')"
          >
            <AppIcon name="spark" aria-hidden="true" />{{
              i18n.t("works.populate_metadata_llm", "Populate metadata with LLM")
            }}
          </button>
          <button
            v-if="props.work.annotations"
            id="overviewAnnotations"
            type="button"
            class="btn"
            @click="emit('annotations')"
          >
            <AppIcon name="record" aria-hidden="true" />{{
              i18n.tf("works.view_annotations", "Annotations ({count})", {
                count: props.work.annotations.toLocaleString(i18n.locale),
              })
            }}
          </button>
        </template>
        <template v-else>
          <button id="browseResearchWork" type="button" class="btn primary" @click="emit('browse')">
            <AppIcon name="search" aria-hidden="true" />{{
              i18n.t("works.browse_records", "Browse records")
            }}
          </button>
          <button
            v-if="props.work.annotations"
            id="researchWorkAnnotations"
            type="button"
            class="btn"
            @click="emit('annotations')"
          >
            <AppIcon name="record" aria-hidden="true" />{{
              i18n.tf("works.view_annotations", "Annotations ({count})", {
                count: props.work.annotations.toLocaleString(i18n.locale),
              })
            }}
          </button>
        </template>
      </div>
    </div>
  </section>
</template>