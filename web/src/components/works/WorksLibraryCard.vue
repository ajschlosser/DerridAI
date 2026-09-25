<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";
import MixedValueInspect from "./MixedValueInspect.vue";
import type { WorksItem } from "../../types/works";
import { statusTone } from "../../domain/status";
import UiStatusBadge from "../ui/UiStatusBadge.vue";

const props = defineProps<{
  work: WorksItem;
  selected?: boolean;
  canSync?: boolean;
  syncDisabledReason?: string;
}>();
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
}>();
const i18n = useI18nStore();

function onCardClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null;
  if (target?.closest("button,details,summary")) return;
  emit("select");
}
</script>
<template>
  <article
    class="card work work-library-card"
    :class="{ selected: props.selected }"
    :data-work="props.work.work"
    @click="onCardClick"
  >
    <div class="work-card-cover">
      <img v-if="props.work.cover" :src="props.work.cover" alt="" loading="lazy" />
      <div v-else class="work-cover-placeholder"><AppIcon name="books" aria-hidden="true" /></div>
    </div>
    <div class="work-card-body">
      <div class="work-top">
        <div class="work-main-copy">
          <div class="work-title-line">
            <h2>{{ props.work.work }}</h2>
            <UiStatusBadge
              :label="props.work.status.label"
              :tone="statusTone(props.work.status.kind)"
              :data-work-status="props.work.work"
            />
          </div>
          <div class="note">
            {{ props.work.authors.join(", ") || i18n.t("works.unknown_author")
            }}<template v-if="props.work.year_label"> · {{ props.work.year_label }}</template>
          </div>
          <div class="work-card-biblio">
            <span v-if="props.work.publisher.mixed">
              {{ props.work.publisher.field_label }}
              <MixedValueInspect
                compact
                :field="'publisher'"
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
                :field="'translator'"
                :field-label="props.work.translator.field_label"
                :count="props.work.translator.unique_count"
                @inspect="emit('inspect', $event)"
              />
            </span>
            <span v-else-if="props.work.translator.value"
              >{{ i18n.t("works.translated_by") }} {{ props.work.translator.value }}</span
            >
          </div>
        </div>
        <div class="work-primary-actions">
          <button
            type="button"
            class="btn small"
            :data-upsert-work="props.work.work"
            :disabled="!props.canSync"
            :data-disabled-reason="props.canSync ? undefined : props.syncDisabledReason"
            :title="props.canSync ? undefined : props.syncDisabledReason"
            @click.stop="emit('sync')"
          >
            <AppIcon name="database" aria-hidden="true" />{{ i18n.t("works.sync") }}
          </button>
          <details class="work-action-menu" @click.stop>
            <summary class="btn small" :title="i18n.t('ui.more_actions')">
              {{ i18n.t("ui.actions") }}
            </summary>
            <div class="work-action-popover">
              <button
                type="button"
                class="btn small"
                :data-populate-work="props.work.work"
                @click.stop="emit('populate')"
              >
                <AppIcon name="spark" aria-hidden="true" />{{
                  i18n.t("works.populate_metadata_llm")
                }}
              </button>
              <button
                type="button"
                class="btn small"
                :data-edit-work-meta="props.work.work"
                @click.stop="emit('edit')"
              >
                <AppIcon name="edit" aria-hidden="true" />{{ i18n.t("works.edit_metadata") }}
              </button>
              <template v-if="props.work.review">
                <button
                  type="button"
                  class="btn small soft"
                  :data-review-work="props.work.work"
                  @click.stop="emit('review')"
                >
                  <AppIcon name="spark" aria-hidden="true" />{{
                    i18n.tf("works.review_flagged", {
                      count: props.work.review,
                    })
                  }}
                </button>
                <button
                  type="button"
                  class="btn small"
                  :data-auto-work="props.work.work"
                  @click.stop="emit('improve')"
                >
                  <AppIcon name="spark" aria-hidden="true" />{{ i18n.t("works.auto_improve") }}
                </button>
              </template>
              <button
                type="button"
                class="btn small danger"
                :data-remove-work="props.work.work"
                @click.stop="emit('remove')"
              >
                <AppIcon name="close" aria-hidden="true" />{{ i18n.t("works.remove_entire") }}
              </button>
            </div>
          </details>
        </div>
      </div>
      <div class="stats">
        <button
          type="button"
          class="stat work-stat-link"
          :data-work-records="props.work.work"
          :aria-label="
            i18n.tf('works.open_records_for_work', {
              count: props.work.count,
              work: props.work.work,
            })
          "
          @click.stop="emit('records')"
        >
          <strong>{{ props.work.count }}</strong
          ><span>{{ i18n.t("dynamic.records") }}</span>
        </button>
        <button
          type="button"
          class="stat work-stat-link"
          :data-work-review="props.work.work"
          :disabled="!props.work.review"
          :aria-label="
            i18n.tf('works.open_review_records_for_work', {
              count: props.work.review,
              work: props.work.work,
            })
          "
          @click.stop="emit('flagged')"
        >
          <strong>{{ props.work.review }}</strong
          ><span>{{ i18n.t("works.need_review") }}</span>
        </button>
        <div class="stat">
          <strong>{{ props.work.files.length }}</strong
          ><span>{{ i18n.t("works.files") }}</span>
        </div>
      </div>
    </div>
  </article>
</template>
