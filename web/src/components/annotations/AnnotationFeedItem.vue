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
import { useI18nStore } from "../../stores/i18n";
import type { AnnotationWorkspaceItem } from "../../types/annotations";
import UiTooltip from "../ui/UiTooltip.vue";

const props = withDefaults(
  defineProps<{ annotation: AnnotationWorkspaceItem; removing?: boolean }>(),
  { removing: false },
);
const emit = defineEmits<{
  open: [annotation: AnnotationWorkspaceItem];
  remove: [annotation: AnnotationWorkspaceItem];
}>();
const i18n = useI18nStore();

function dateLabel(value: string | null) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(i18n.locale, {
    timeZone: i18n.timeZone,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
</script>

<template>
  <article class="annotation-feed-item">
    <UiTooltip
      :text="i18n.t('annotations.open_record')"
      trigger-mode="content"
      :content-focusable="false"
      placement="bottom"
    >
      <button
        class="annotation-open-record"
        type="button"
        :aria-label="i18n.t('annotations.open_record')"
        @click="emit('open', props.annotation)"
      >
        <span aria-hidden="true">↗</span>
      </button>
    </UiTooltip>
    <div class="annotation-feed-copy">
      <div class="annotation-feed-meta">
        <b>{{ props.annotation.record_id }}</b>
        <span>{{ props.annotation.field }}</span>
        <time>{{ dateLabel(props.annotation.created_at) }}</time>
      </div>
      <p v-if="props.annotation.deleted_at" class="annotation-deleted">
        {{ i18n.t("annotations.deleted") }}
      </p>
      <blockquote v-else-if="props.annotation.quote">{{ props.annotation.quote }}</blockquote>
      <p v-if="!props.annotation.deleted_at && props.annotation.note">
        {{ props.annotation.note }}
      </p>
      <div v-if="props.annotation.tags.length" class="annotation-tags">
        <span v-for="tag in props.annotation.tags" :key="tag" class="chip">{{ tag }}</span>
      </div>
      <small>{{ props.annotation.author }} · {{ props.annotation.source }}</small>
    </div>
    <button
      v-if="props.annotation.removable"
      class="btn tiny danger"
      type="button"
      :disabled="props.removing"
      @click="emit('remove', props.annotation)"
    >
      {{ props.removing ? i18n.t("ui.removing") : i18n.t("ui.remove") }}
    </button>
  </article>
</template>
