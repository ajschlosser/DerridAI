<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../../stores/i18n";
import { statusTone } from "../../domain/status";
import type { WorksLibraryItem } from "../../types/works";
import AppIcon from "../AppIcon.vue";
import UiButton from "../ui/UiButton.vue";
import UiMenu, { type UiMenuItem } from "../ui/UiMenu.vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";

const props = withDefaults(
  defineProps<{
    works: WorksLibraryItem[];
    selectedWork?: string;
    mode?: "admin" | "researcher";
    canSync?: boolean;
    syncDisabledReason?: string;
  }>(),
  { selectedWork: "", mode: "admin", canSync: false, syncDisabledReason: "" },
);

const emit = defineEmits<{
  select: [work: string];
  sync: [work: string];
  populate: [work: string];
  edit: [work: string];
  review: [work: string];
  improve: [work: string];
  remove: [work: string];
  records: [work: string];
  flagged: [work: string];
  semanticMap: [work: string];
}>();

const i18n = useI18nStore();
const admin = computed(() => props.mode === "admin");

function byline(work: WorksLibraryItem) {
  const author = work.authors.join(", ") || i18n.t("works.unknown_author");
  return work.year_label ? `${author} · ${work.year_label}` : author;
}

function menuItems(work: WorksLibraryItem): UiMenuItem[] {
  const items: UiMenuItem[] = [
    { id: "populate", label: i18n.t("works.populate_metadata_llm"), icon: "spark" },
    { id: "edit", label: i18n.t("works.edit_metadata"), icon: "edit" },
  ];
  if (work.review) {
    items.push(
      {
        id: "review",
        label: i18n.tf("works.review_flagged", { count: work.review }),
        icon: "record",
      },
      { id: "improve", label: i18n.t("works.auto_improve"), icon: "spark" },
    );
  }
  items.push(
    { id: "semantic-map", label: i18n.t("works.semantic_map"), icon: "compare" },
    {
      id: "sync",
      label: i18n.t("works.sync_work"),
      icon: "database",
      reason: props.canSync ? undefined : props.syncDisabledReason || undefined,
    },
    { id: "remove", label: i18n.t("works.remove_entire"), icon: "close" },
  );
  return items;
}

function onMenu(work: WorksLibraryItem, id: string) {
  const commands: Record<string, () => void> = {
    populate: () => emit("populate", work.work),
    edit: () => emit("edit", work.work),
    review: () => emit("review", work.work),
    improve: () => emit("improve", work.work),
    "semantic-map": () => emit("semanticMap", work.work),
    sync: () => emit("sync", work.work),
    remove: () => emit("remove", work.work),
  };
  commands[id]?.();
}
</script>

<template>
  <div class="works-list-shell">
    <table class="ui-table works-list">
      <thead>
        <tr>
          <th scope="col">{{ i18n.t("works.list_work") }}</th>
          <th scope="col">{{ i18n.t("works.list_author_year") }}</th>
          <th scope="col" class="numeric">{{ i18n.t("dynamic.records") }}</th>
          <th v-if="admin" scope="col" class="numeric">{{ i18n.t("works.need_review") }}</th>
          <th v-if="admin" scope="col">{{ i18n.t("works.list_index_status") }}</th>
          <th scope="col" class="actions">
            <span class="sr-only">{{ i18n.t("ui.actions") }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="work in props.works"
          :key="work.work"
          :class="{ selected: props.selectedWork === work.work }"
          :data-work="work.work"
        >
          <td class="works-list-identity">
            <button
              type="button"
              class="works-list-select"
              :aria-pressed="props.selectedWork === work.work"
              :data-select-work="work.work"
              @click="emit('select', work.work)"
            >
              <span class="works-list-cover" aria-hidden="true">
                <img v-if="work.cover" :src="work.cover" alt="" loading="lazy" />
                <AppIcon v-else name="books" aria-hidden="true" />
              </span>
              <span class="works-list-title">{{ work.work }}</span>
            </button>
          </td>
          <td class="works-list-byline">{{ byline(work) }}</td>
          <td class="numeric">
            <button
              type="button"
              class="works-list-count"
              :aria-label="
                i18n.tf('works.open_records_for_work', { count: work.count, work: work.work })
              "
              @click="emit('records', work.work)"
            >
              {{ work.count.toLocaleString(i18n.locale) }}
            </button>
          </td>
          <td v-if="admin" class="numeric">
            <button
              type="button"
              class="works-list-count"
              :class="{ attention: work.review > 0 }"
              :disabled="!work.review"
              :aria-label="
                i18n.tf('works.open_review_records_for_work', {
                  count: work.review,
                  work: work.work,
                })
              "
              @click="emit('flagged', work.work)"
            >
              {{ work.review.toLocaleString(i18n.locale) }}
            </button>
          </td>
          <td v-if="admin">
            <UiStatusBadge :label="work.status.label" :tone="statusTone(work.status.kind)" />
          </td>
          <td class="actions">
            <UiButton
              v-if="!admin"
              size="small"
              :label="i18n.t('works.open_records')"
              @click="emit('records', work.work)"
            />
            <UiMenu
              v-else
              :label="i18n.t('ui.actions')"
              :aria-label="i18n.tf('works.work_actions', { work: work.work })"
              :items="menuItems(work)"
              align="end"
              @select="onMenu(work, $event)"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.works-list-shell {
  min-width: 0;
  overflow: auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.works-list {
  width: 100%;
  min-width: 48rem;
  border-collapse: collapse;
}
.works-list th,
.works-list td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
  vertical-align: middle;
}
.works-list tbody tr:last-child td {
  border-bottom: 0;
}
.works-list th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--surface-raised);
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  text-align: start;
}
.works-list tr.selected td {
  background: var(--surface-selected);
}
.works-list tr.selected td:first-child {
  box-shadow: inset 4px 0 0 var(--accent-fg);
}
.works-list .numeric {
  width: 1%;
  text-align: end;
  white-space: nowrap;
}
.works-list .actions {
  width: 1%;
  text-align: end;
  white-space: nowrap;
}
.works-list-select {
  display: inline-grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--space-2);
  align-items: center;
  min-width: 0;
  max-width: 30rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: start;
  cursor: pointer;
}
.works-list-select:focus-visible,
.works-list-count:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.works-list-cover {
  display: grid;
  place-items: center;
  width: 2rem;
  height: 3rem;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: 2px var(--radius-control) var(--radius-control) 2px;
  background: var(--surface-inset);
  color: var(--text-secondary);
}
.works-list-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.works-list-title {
  color: var(--text-primary);
  font-weight: var(--fw-semibold);
  overflow-wrap: anywhere;
}
.works-list-byline {
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.works-list-count {
  min-width: var(--control-height-small);
  min-height: var(--control-height-small);
  padding-inline: var(--space-2);
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--accent-fg);
  font: inherit;
  font-weight: var(--fw-semibold);
  cursor: pointer;
}
.works-list-count:hover:not(:disabled) {
  background: var(--surface-raised);
}
.works-list-count:disabled {
  color: var(--text-secondary);
  cursor: default;
}
.works-list-count.attention {
  color: var(--tone-warn-fg);
}
@media (max-width: 760px) {
  .works-list {
    min-width: 42rem;
  }
}
</style>
