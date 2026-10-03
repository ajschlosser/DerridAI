<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";
import MixedValueInspect from "./MixedValueInspect.vue";
import type { WorksLibraryItem } from "../../types/works";
import { statusTone } from "../../domain/status";
import UiButton from "../ui/UiButton.vue";
import UiMenu, { type UiMenuItem } from "../ui/UiMenu.vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";

const props = withDefaults(
  defineProps<{
    work: WorksLibraryItem;
    selected?: boolean;
    /** Researcher libraries are read-only: no database status, no corpus operations. */
    mode?: "admin" | "researcher";
    canSync?: boolean;
    syncDisabledReason?: string;
  }>(),
  { selected: false, mode: "admin", canSync: false, syncDisabledReason: "" },
);
const emit = defineEmits<{
  select: [];
  sync: [];
  populate: [];
  edit: [];
  review: [];
  improve: [];
  remove: [];
  records: [];
  flagged: [];
  inspect: [field: string];
  semanticMap: [];
}>();
const i18n = useI18nStore();

const admin = computed(() => props.mode === "admin");
const byline = computed(() => {
  if (!admin.value) return props.work.subtitle;
  const author = props.work.authors.join(", ") || i18n.t("works.unknown_author");
  return props.work.year_label ? `${author} · ${props.work.year_label}` : author;
});
const menuItems = computed<UiMenuItem[]>(() => {
  const items: UiMenuItem[] = [
    { id: "populate", label: i18n.t("works.populate_metadata_llm"), icon: "spark" },
    { id: "edit", label: i18n.t("works.edit_metadata"), icon: "edit" },
  ];
  if (props.work.review) {
    items.push(
      {
        id: "review",
        label: i18n.tf("works.review_flagged", { count: props.work.review }),
        icon: "spark",
      },
      { id: "improve", label: i18n.t("works.auto_improve"), icon: "spark" },
    );
  }
  items.push(
    { id: "semantic-map", label: i18n.t("works.semantic_map"), icon: "spark" },
    {
      id: "sync",
      label: i18n.t("works.sync_work"),
      icon: "database",
      reason: props.canSync ? undefined : props.syncDisabledReason || undefined,
    },
    { id: "remove", label: i18n.t("works.remove_entire"), icon: "close" },
  );
  return items;
});

function onMenu(id: string) {
  const commands: Record<string, () => void> = {
    populate: () => emit("populate"),
    edit: () => emit("edit"),
    review: () => emit("review"),
    improve: () => emit("improve"),
    "semantic-map": () => emit("semanticMap"),
    sync: () => emit("sync"),
    remove: () => emit("remove"),
  };
  commands[id]?.();
}
</script>

<template>
  <article class="works-card" :class="{ selected: props.selected }" :data-work="props.work.work">
    <button
      type="button"
      class="works-card-select"
      :aria-pressed="props.selected"
      :data-select-work="props.work.work"
      @click="emit('select')"
    >
      <span class="works-card-cover" aria-hidden="true">
        <img v-if="props.work.cover" :src="props.work.cover" alt="" loading="lazy" />
        <AppIcon v-else name="books" aria-hidden="true" />
      </span>
      <span class="works-card-identity">
        <span class="works-card-title">{{ props.work.work }}</span>
        <span class="works-card-byline">{{ byline }}</span>
      </span>
      <span v-if="props.selected" class="works-card-selected">
        <AppIcon name="check" aria-hidden="true" />{{ i18n.t("works.selected") }}
      </span>
    </button>

    <div v-if="admin" class="works-card-biblio">
      <span v-if="props.work.publisher.mixed">
        {{ props.work.publisher.field_label }}
        <MixedValueInspect
          compact
          field="publisher"
          :field-label="props.work.publisher.field_label"
          :count="props.work.publisher.unique_count"
          @inspect="emit('inspect', $event)"
        />
      </span>
      <span v-else-if="props.work.publisher.value">{{ props.work.publisher.value }}</span>
      <span v-if="props.work.translator.mixed">
        {{ i18n.t("works.translated_by") }}
        <MixedValueInspect
          compact
          field="translator"
          :field-label="props.work.translator.field_label"
          :count="props.work.translator.unique_count"
          @inspect="emit('inspect', $event)"
        />
      </span>
      <span v-else-if="props.work.translator.value"
        >{{ i18n.t("works.translated_by") }} {{ props.work.translator.value }}</span
      >
    </div>

    <div class="works-card-footer">
      <button
        type="button"
        class="works-card-stat"
        :data-work-records="props.work.work"
        :aria-label="
          i18n.tf('works.open_records_for_work', {
            count: props.work.count,
            work: props.work.work,
          })
        "
        @click="emit('records')"
      >
        <strong>{{ props.work.count.toLocaleString(i18n.locale) }}</strong>
        <span>{{ i18n.t("dynamic.records") }}</span>
      </button>
      <button
        v-if="admin"
        type="button"
        class="works-card-stat"
        :class="{ attention: props.work.review > 0 }"
        :data-work-review="props.work.work"
        :disabled="!props.work.review"
        :aria-label="
          i18n.tf('works.open_review_records_for_work', {
            count: props.work.review,
            work: props.work.work,
          })
        "
        @click="emit('flagged')"
      >
        <strong>{{ props.work.review.toLocaleString(i18n.locale) }}</strong>
        <span>{{ i18n.t("works.need_review") }}</span>
      </button>
      <UiStatusBadge
        v-if="admin"
        :label="props.work.status.label"
        :tone="statusTone(props.work.status.kind)"
        :data-work-status="props.work.work"
      />
      <span class="works-card-actions">
        <UiButton
          v-if="!admin"
          size="small"
          variant="primary"
          :label="i18n.t('works.open_records')"
          @click="emit('records')"
        />
        <UiMenu
          v-else
          :label="i18n.t('ui.actions')"
          :aria-label="i18n.tf('works.work_actions', { work: props.work.work })"
          :items="menuItems"
          align="end"
          @select="onMenu"
        />
      </span>
    </div>
  </article>
</template>

<style scoped>
.works-card {
  display: grid;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.works-card.selected {
  border-color: var(--accent-border);
  background: var(--surface-selected);
  box-shadow: inset 4px 0 0 var(--accent-fg);
}
.works-card-select {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--space-3);
  align-items: start;
  width: 100%;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  text-align: start;
  cursor: pointer;
}
.works-card-select:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
  border-radius: var(--radius-control);
}
.works-card-cover {
  display: grid;
  place-items: center;
  width: 4rem;
  height: 6rem;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: 2px var(--radius-control) var(--radius-control) 2px;
  background: var(--surface-inset);
  color: var(--text-secondary);
}
.works-card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.works-card-identity {
  display: grid;
  gap: var(--space-1);
  min-width: 0;
}
.works-card-title {
  color: var(--text-primary);
  font-size: var(--fs-lg);
  font-weight: var(--fw-bold);
  line-height: var(--lh-tight);
  overflow-wrap: anywhere;
}
.works-card-byline {
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  overflow-wrap: anywhere;
}
.works-card-selected {
  grid-column: 2;
  display: inline-flex;
  gap: var(--space-1);
  align-items: center;
  color: var(--accent-fg);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
}
.works-card-biblio {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.works-card-footer {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-3);
  align-items: center;
}
.works-card-stat {
  display: inline-flex;
  gap: var(--space-1);
  align-items: baseline;
  min-height: var(--control-height-small);
  padding: 0 var(--space-2);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-raised);
  color: var(--text-primary);
  font: inherit;
  font-size: var(--fs-sm);
  cursor: pointer;
}
.works-card-stat:disabled {
  color: var(--text-secondary);
  cursor: default;
}
.works-card-stat.attention {
  border-color: var(--tone-warn-edge);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.works-card-stat:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.works-card-actions {
  margin-inline-start: auto;
}
</style>
