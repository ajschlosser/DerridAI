<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
export type TooltipInfoboxRow = {
  label: string;
  value: string;
};

defineProps<{
  title: string;
  description?: string;
  rows?: TooltipInfoboxRow[];
}>();
</script>

<template>
  <aside class="tooltip-infobox" role="region" :aria-label="title">
    <strong>{{ title }}</strong>
    <p v-if="description">{{ description }}</p>
    <table v-if="rows?.length">
      <tbody>
        <tr v-for="row in rows" :key="row.label">
          <th scope="row">{{ row.label }}</th>
          <td>{{ row.value }}</td>
        </tr>
      </tbody>
    </table>
    <slot />
  </aside>
</template>

<style scoped>
.tooltip-infobox {
  position: absolute;
  z-index: 5;
  inset-block-start: 0;
  inset-block-end: auto;
  inset-inline-start: 0;
  inline-size: min(19rem, calc(100vw - 2rem));
  padding: 11px 12px;
  border: 1px solid var(--line-strong);
  border-radius: 10px;
  background: var(--card);
  color: var(--text);
  box-shadow: var(--shadow-overlay, 0 12px 30px rgb(0 0 0 / 20%));
  pointer-events: none;
}
.tooltip-infobox::after {
  position: absolute;
  inset-block-end: -6px;
  inset-inline-start: 18px;
  inline-size: 10px;
  block-size: 10px;
  border-inline-end: 1px solid var(--line-strong);
  border-block-end: 1px solid var(--line-strong);
  background: var(--card);
  content: "";
  transform: rotate(45deg);
}
.tooltip-infobox strong {
  display: block;
  font-size: 0.8rem;
}
.tooltip-infobox p {
  margin: 4px 0 8px;
  color: var(--muted);
  font-size: 0.75rem;
  line-height: 1.4;
}
.tooltip-infobox table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
}
.tooltip-infobox th,
.tooltip-infobox td {
  padding: 4px 0;
  border-top: 1px solid var(--line);
  text-align: start;
  vertical-align: top;
}
.tooltip-infobox th {
  width: 42%;
  color: var(--muted);
  font-weight: 700;
}
.tooltip-infobox td {
  overflow-wrap: anywhere;
}
</style>
