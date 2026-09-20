<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";
import type { AnnotationWorkspaceItem } from "../../types/annotations";

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
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
</script>

<template>
  <article class="annotation-feed-item">
    <button
      class="annotation-open-record"
      type="button"
      :title="i18n.t('annotations.open_record', 'Open record')"
      @click="emit('open', props.annotation)"
    >
      <span aria-hidden="true">↗</span>
    </button>
    <div class="annotation-feed-copy">
      <div class="annotation-feed-meta">
        <b>{{ props.annotation.record_id }}</b>
        <span>{{ props.annotation.field }}</span>
        <time>{{ dateLabel(props.annotation.created_at) }}</time>
      </div>
      <blockquote v-if="props.annotation.quote">{{ props.annotation.quote }}</blockquote>
      <p v-if="props.annotation.note">{{ props.annotation.note }}</p>
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
      {{ props.removing ? i18n.t("ui.removing", "Removing…") : i18n.t("ui.remove", "Remove") }}
    </button>
  </article>
</template>
