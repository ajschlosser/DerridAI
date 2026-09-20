<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
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
      :class="{changed: row.changed, text: row.key === 'text'}"
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
.compare-diff{display:grid;gap:12px}
.compare-diff-empty{padding:18px;border:1px dashed var(--line);border-radius:14px;color:var(--muted);font-size:.875rem}
.compare-diff-card{overflow:hidden;border:1px solid var(--line);border-radius:14px;background:var(--panel)}
.compare-diff-card.changed{box-shadow:inset 3px 0 0 var(--accent)}
.compare-diff-card header{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;padding:10px 14px;background:var(--panel-2);border-bottom:1px solid var(--line)}
.compare-diff-card h3{margin:0;font-size:.9375rem;line-height:1.3}
.compare-diff-card code,.compare-diff-card span{color:var(--muted);font-size:.8125rem}
.compare-diff-sides{display:grid;grid-template-columns:1fr 1fr}
.compare-diff-sides section{min-width:0;padding:12px 14px}
.compare-diff-sides section+section{border-left:1px solid var(--line)}
.compare-side-kicker{margin:0 0 8px;font-size:.8125rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--accent-2,var(--accent))}
pre{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;font-size:14px;line-height:1.5;min-height:1.5em;color:var(--text)}
pre :deep(.del),pre span.del{color:#3f1010 !important;background:#f7d2d2;text-decoration:line-through;font-weight:700;font-size:14px}
pre :deep(.ins),pre span.ins{color:#10281c !important;background:#cfe8d6;font-weight:700;font-size:14px}
@media (max-width:800px){
  .compare-diff-sides{grid-template-columns:1fr}
  .compare-diff-sides section+section{border-left:0;border-top:1px solid var(--line)}
}
@media (forced-colors: active){
  .compare-diff-card.changed{outline:2px solid CanvasText}
  .del,.ins{outline:1px solid CanvasText}
}
@media (prefers-reduced-motion: reduce){
  .compare-diff-card{transition:none}
}
</style>
