<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";
import MixedValueInspect from "./MixedValueInspect.vue";
import WorksInsightCard from "./WorksInsightCard.vue";
import type { WorkDetail } from "../../types/works";
import { statusTone } from "../../domain/status";
import UiButton from "../ui/UiButton.vue";
import UiMenu, { type UiMenuItem } from "../ui/UiMenu.vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";

/** The selected work's details. It is inspector content: it sits beside the library (or inside a dialog)
 *  and never introduces a page-level heading. */
const props = withDefaults(
  defineProps<{
    work: WorkDetail;
    mode?: "admin" | "researcher";
    citationLabel?: string;
    /** Show a close control (the persistent inspector); the dialog supplies its own. */
    closable?: boolean;
    /** The surrounding dialog already names the work, so the heading is not repeated. */
    embedded?: boolean;
    canSync?: boolean;
    syncDisabledReason?: string;
  }>(),
  {
    mode: "admin",
    citationLabel: "",
    closable: false,
    embedded: false,
    canSync: false,
    syncDisabledReason: "",
  },
);
const emit = defineEmits<{
  search: [];
  review: [];
  edit: [];
  populate: [];
  annotations: [];
  browse: [];
  semanticMap: [];
  sync: [];
  close: [];
  inspect: [field: string];
  insight: [field: string, value: string];
}>();
const i18n = useI18nStore();

const admin = computed(() => props.mode === "admin");
const menuItems = computed<UiMenuItem[]>(() => {
  const items: UiMenuItem[] = [
    { id: "populate", label: i18n.t("works.populate_metadata_llm"), icon: "spark" },
    { id: "semantic-map", label: i18n.t("works.semantic_map"), icon: "spark" },
  ];
  if (props.work.annotations) {
    items.push({
      id: "annotations",
      label: i18n.tf("works.view_annotations", {
        count: props.work.annotations.toLocaleString(i18n.locale),
      }),
      icon: "record",
    });
  }
  items.push({
    id: "sync",
    label: i18n.t("works.sync_work"),
    icon: "database",
    reason: props.canSync ? undefined : props.syncDisabledReason || undefined,
  });
  return items;
});
function onMenu(id: string) {
  if (id === "populate") emit("populate");
  else if (id === "semantic-map") emit("semanticMap");
  else if (id === "annotations") emit("annotations");
  else if (id === "sync") emit("sync");
}
</script>
<template>
  <section
    class="works-inspector"
    :aria-labelledby="props.embedded ? undefined : 'selected-work-title'"
    :aria-label="props.embedded ? i18n.t('works.inspector_label') : undefined"
  >
    <header class="works-inspector-masthead">
      <figure class="works-inspector-cover" :aria-hidden="props.work.cover ? undefined : true">
        <img
          v-if="props.work.cover"
          :src="props.work.cover"
          :alt="i18n.tf('works.cover_alt', { work: props.work.work })"
          loading="lazy"
        />
        <AppIcon v-else name="books" aria-hidden="true" />
      </figure>
      <div class="works-inspector-heading">
        <h2 v-if="!props.embedded" id="selected-work-title">{{ props.work.work }}</h2>
        <p>
          {{ props.work.count.toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.records") }}
          <template v-if="admin">
            ·
            {{ props.work.review.toLocaleString(i18n.locale) }} {{ i18n.t("works.need_review") }}
            ·
            {{ props.work.files.length.toLocaleString(i18n.locale) }}
            {{ i18n.t("works.source_files") }}
          </template>
        </p>
        <UiStatusBadge
          v-if="admin"
          :label="props.work.status.label"
          :tone="statusTone(props.work.status.kind)"
          :data-work-status="props.work.work"
        />
      </div>
      <UiButton
        v-if="props.closable"
        size="small"
        variant="ghost"
        icon-only
        icon="close"
        :label="i18n.t('works.close_inspector')"
        @click="emit('close')"
      />
    </header>

    <div class="works-inspector-actions">
      <template v-if="admin">
        <UiButton
          variant="primary"
          icon="search"
          :label="i18n.t('works.open_records')"
          @click="emit('search')"
        />
        <UiButton
          v-if="props.work.review"
          icon="spark"
          :label="i18n.t('works.review_records')"
          :count="props.work.review"
          @click="emit('review')"
        />
        <UiButton icon="edit" :label="i18n.t('works.edit_metadata')" @click="emit('edit')" />
        <UiMenu
          :label="i18n.t('ui.more_actions')"
          :menu-label="i18n.t('works.more_work_actions')"
          :items="menuItems"
          align="end"
          @select="onMenu"
        />
      </template>
      <template v-else>
        <UiButton
          variant="primary"
          icon="search"
          :label="i18n.t('works.browse_records')"
          @click="emit('browse')"
        />
        <UiButton
          v-if="props.work.annotations"
          icon="record"
          :label="
            i18n.tf('works.view_annotations', {
              count: props.work.annotations.toLocaleString(i18n.locale),
            })
          "
          @click="emit('annotations')"
        />
      </template>
    </div>

    <dl class="works-inspector-metadata">
      <div v-for="item in props.work.metadata" :key="item.field">
        <dt>{{ item.field_label }}</dt>
        <dd>
          <MixedValueInspect
            v-if="item.mixed"
            :field="item.field"
            :field-label="item.field_label"
            :count="item.unique_count"
            @inspect="emit('inspect', $event)"
          />
          <template v-else>{{ item.value }}</template>
        </dd>
      </div>
    </dl>

    <div v-if="admin || props.work.citation" class="works-inspector-citation">
      <h3>{{ props.citationLabel }}</h3>
      <p>{{ props.work.citation }}</p>
    </div>

    <details v-if="admin" class="works-inspector-insights">
      <summary>{{ i18n.t("works.insights_toggle") }}</summary>
      <p class="works-inspector-note">{{ i18n.t("works.work_insights_help") }}</p>
      <div class="works-inspector-insight-grid">
        <WorksInsightCard
          v-for="insight in props.work.insights"
          :key="insight.id"
          :insight="insight"
          @search="(field, value) => emit('insight', field, value)"
        />
      </div>
    </details>
  </section>
</template>

<style scoped>
.works-inspector {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
}
.works-inspector-masthead {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: var(--space-4);
  align-items: start;
}
.works-inspector-cover {
  display: grid;
  place-items: center;
  width: 6rem;
  height: 9rem;
  margin: 0;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: 2px var(--radius-control) var(--radius-control) 2px;
  background: var(--surface-inset);
  color: var(--text-secondary);
}
.works-inspector-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.works-inspector-heading {
  display: grid;
  gap: var(--space-2);
  justify-items: start;
  min-width: 0;
}
.works-inspector-heading h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--fs-xl);
  line-height: var(--lh-tight);
  overflow-wrap: anywhere;
}
.works-inspector-heading p {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.works-inspector-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.works-inspector-metadata {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr));
  gap: var(--space-2);
  margin: 0;
}
.works-inspector-metadata > div {
  min-width: 0;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-raised);
}
.works-inspector-metadata dt {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.works-inspector-metadata dd {
  margin: 2px 0 0;
  color: var(--text-primary);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
  overflow-wrap: anywhere;
}
.works-inspector-citation h3 {
  margin: 0 0 var(--space-1);
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.works-inspector-citation p,
.works-inspector-note {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.works-inspector-note {
  margin-block: var(--space-2);
  color: var(--text-secondary);
}
.works-inspector-insights {
  border-top: 1px solid var(--border-subtle);
  padding-top: var(--space-3);
}
.works-inspector-insights summary {
  color: var(--text-primary);
  font-weight: var(--fw-semibold);
  cursor: pointer;
}
.works-inspector-insights summary:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.works-inspector-insight-grid {
  display: grid;
  gap: var(--space-3);
}
@media (max-width: 520px) {
  .works-inspector-masthead {
    grid-template-columns: auto minmax(0, 1fr);
  }
  .works-inspector-cover {
    width: 4.5rem;
    height: 6.75rem;
  }
}
</style>
