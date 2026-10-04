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
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed } from "vue";
import type { CorpusBuild } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";

const props = withDefaults(
  defineProps<{
    build: CorpusBuild;
    limit?: number;
  }>(),
  { limit: 4 },
);
const i18n = useI18nStore();

const events = computed(() =>
  [...(props.build.build_events || [])]
    .filter((event) => event && (event.stage || event.status))
    .reverse()
    .slice(0, Math.max(1, props.limit)),
);

function stageLabel(stage?: string, status?: string) {
  const value = String(stage || status || "");
  return i18n.t(`pdf_corpus.stage.${value}`, value.replace(/_/g, " "));
}

function when(value?: string) {
  if (!value) return "";
  try {
    return new Intl.DateTimeFormat(i18n.locale || undefined, {
      timeZone: i18n.timeZone,
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return value;
  }
}
</script>

<template>
  <section
    v-if="events.length > 1"
    class="build-activity"
    :aria-label="i18n.t('pdf_corpus.build_timeline')"
  >
    <span class="build-activity-label">{{ i18n.t("pdf_corpus.build_timeline") }}</span>
    <ol>
      <li v-for="(event, index) in events" :key="`${event.at}-${event.stage}-${index}`">
        <span class="build-activity-dot" aria-hidden="true"></span>
        <span class="build-activity-copy">
          <b>{{ stageLabel(event.stage, event.status) }}</b>
          <small>
            <template v-if="when(event.at)">{{ when(event.at) }} · </template>
            {{ Math.round(Number(event.progress || 0) * 100) }}%
          </small>
        </span>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.build-activity {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--space-3);
  align-items: center;
  min-width: 0;
  padding: var(--space-2) var(--space-3);
  border-block: 1px solid var(--border-subtle);
}
.build-activity-label {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.build-activity ol {
  display: flex;
  min-width: 0;
  gap: var(--space-2) var(--space-4);
  align-items: center;
  margin: 0;
  padding: 0;
  list-style: none;
  overflow-x: auto;
  scrollbar-width: thin;
}
.build-activity li {
  display: inline-flex;
  flex: 0 0 auto;
  gap: var(--space-2);
  align-items: center;
}
.build-activity-dot {
  width: 0.45rem;
  height: 0.45rem;
  flex: none;
  border-radius: 999px;
  background: var(--ui-accent);
}
.build-activity-copy {
  display: grid;
  gap: 1px;
}
.build-activity b,
.build-activity small {
  font-size: var(--fs-xs);
  line-height: 1.3;
}
.build-activity small {
  color: var(--text-secondary);
}
@media (max-width: 720px) {
  .build-activity {
    grid-template-columns: 1fr;
  }
}
</style>
