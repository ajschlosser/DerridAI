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
import type { CompareFieldRow } from "../../domain/compare";

defineProps<{
  rows: CompareFieldRow[];
  emptyLabel: string;
  changedLabel: string;
  identicalLabel: string;
  sideA: string;
  sideB: string;
}>();
</script>
<template>
  <div class="compare-diff" role="list">
    <article v-if="!rows.length" class="compare-diff-empty">{{ emptyLabel }}</article>
    <article
      v-for="row in rows"
      :key="row.key"
      class="compare-diff-card"
      :class="{ changed: row.changed, text: row.key === 'text' }"
      role="listitem"
    >
      <header>
        <div>
          <h3>{{ row.label }}</h3>
          <code>{{ row.key }}</code>
        </div>
        <span>{{ row.changed ? changedLabel : identicalLabel }}</span>
      </header>
      <div class="compare-diff-sides">
        <section :aria-label="sideA">
          <p class="compare-side-kicker">{{ sideA }}</p>
          <pre><span v-for="(part, index) in row.parts.filter(item => item.kind !== 'ins')" :key="`l${index}`" :class="part.kind">{{ part.value }}</span></pre>
        </section>
        <section :aria-label="sideB">
          <p class="compare-side-kicker">{{ sideB }}</p>
          <pre><span v-for="(part, index) in row.parts.filter(item => item.kind !== 'del')" :key="`r${index}`" :class="part.kind">{{ part.value }}</span></pre>
        </section>
      </div>
    </article>
  </div>
</template>
<style scoped>
.compare-diff {
  display: grid;
  gap: 12px;
}
.compare-diff-empty {
  padding: 18px;
  border: 1px dashed var(--line);
  border-radius: 14px;
  color: var(--muted);
  font-size: 0.875rem;
}
.compare-diff-card {
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--panel);
}
.compare-diff-card.changed {
  box-shadow: inset 3px 0 0 var(--accent);
}
.compare-diff-card header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  padding: 10px 14px;
  background: var(--panel-2);
  border-bottom: 1px solid var(--line);
}
.compare-diff-card h3 {
  margin: 0;
  font-size: 0.9375rem;
  line-height: 1.3;
}
.compare-diff-card code,
.compare-diff-card span {
  color: var(--muted);
  font-size: 0.8125rem;
}
.compare-diff-sides {
  display: grid;
  grid-template-columns: 1fr 1fr;
}
.compare-diff-sides section {
  min-width: 0;
  padding: 12px 14px;
}
.compare-diff-sides section + section {
  border-left: 1px solid var(--line);
}
.compare-side-kicker {
  margin: 0 0 8px;
  font-size: 0.8125rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--accent-fg);
}
pre {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: inherit;
  font-size: 0.875rem;
  line-height: 1.5;
  min-height: 1.5em;
  color: var(--text);
}
pre :deep(.del),
pre span.del {
  color: var(--tone-danger-fg) !important;
  background: var(--tone-danger-bg);
  text-decoration: line-through;
  font-weight: 700;
  font-size: 0.875rem;
}
pre :deep(.ins),
pre span.ins {
  color: var(--text) !important;
  background: var(--tone-ok-bg);
  font-weight: 700;
  font-size: 0.875rem;
}
@media (max-width: 800px) {
  .compare-diff-sides {
    grid-template-columns: 1fr;
  }
  .compare-diff-sides section + section {
    border-left: 0;
    border-top: 1px solid var(--line);
  }
}
@media (forced-colors: active) {
  .compare-diff-card.changed {
    outline: 2px solid CanvasText;
  }
  .del,
  .ins {
    outline: 1px solid CanvasText;
  }
}
@media (prefers-reduced-motion: reduce) {
  .compare-diff-card {
    transition: none;
  }
}
</style>
